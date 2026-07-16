#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CURSOR="$SCRIPT_DIR/library/cursor"
HOOKS_FULL="$SCRIPT_DIR/library/cursor/hooks.full.json"
SEARCH_ROOT="$HOME/redhat"

DRY_RUN=false
AUTO_YES=false
VERBOSE=false

TMPDIR_SYNC="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_SYNC"' EXIT

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Sync .cursor/ config (rules, skills, hooks, references) from rules-skills
to all projects under ~/redhat.

Strategy: add new files, update changed files, delete stale files in managed
directories (rules/, hooks/, references/). Project-specific extras outside
managed dirs are never touched.

Options:
  --dry-run   Show what would change without modifying anything
  --yes       Skip confirmation prompt
  --verbose   Show per-file detail for new/changed/stale files
  -h, --help  Show this help
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)  DRY_RUN=true; shift ;;
        --yes)      AUTO_YES=true; shift ;;
        --verbose)  VERBOSE=true; shift ;;
        -h|--help)  usage ;;
        *)          echo "Unknown option: $1"; usage ;;
    esac
done

BOLD="\033[1m"
DIM="\033[2m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

MANAGED_DIRS=(rules hooks references)

SOURCE_FILES_LIST="$TMPDIR_SYNC/source_files"
find "$SOURCE_CURSOR" -type f \
    ! -name '.DS_Store' \
    ! -path '*/agents/*' \
    ! -path '*/skills/*' \
    ! -name '.evaluator-active' \
    ! -name '.commit-approved' \
    | sort > "$SOURCE_FILES_LIST"

# Add hooks.full.json as the hooks.json for targets (full enforcement)
echo "$HOOKS_FULL" >> "$SOURCE_FILES_LIST"

resolve_target_path() {
    local src_file="$1"
    local target_cursor="$2"
    if [[ "$src_file" == "$HOOKS_FULL" ]]; then
        echo "$target_cursor/hooks.json"
    else
        echo "$target_cursor/${src_file#$SOURCE_CURSOR/}"
    fi
}

resolve_rel_path() {
    local src_file="$1"
    if [[ "$src_file" == "$HOOKS_FULL" ]]; then
        echo "hooks.json (full enforcement)"
    else
        echo "${src_file#$SOURCE_CURSOR/}"
    fi
}

compare_project() {
    local rel="$1"
    local target_cursor="$SEARCH_ROOT/$rel/.cursor"
    local new_count=0
    local changed_count=0
    local uptodate_count=0
    local stale_count=0
    local new_files=""
    local changed_files=""
    local stale_files=""

    while IFS= read -r src_file; do
        local target_file
        target_file="$(resolve_target_path "$src_file" "$target_cursor")"
        local rel_file
        rel_file="$(resolve_rel_path "$src_file")"

        if [[ ! -f "$target_file" ]]; then
            new_count=$((new_count + 1))
            new_files="${new_files}  + ${rel_file}\n"
        elif ! diff -q "$src_file" "$target_file" > /dev/null 2>&1; then
            changed_count=$((changed_count + 1))
            changed_files="${changed_files}  ~ ${rel_file}\n"
        else
            uptodate_count=$((uptodate_count + 1))
        fi
    done < "$SOURCE_FILES_LIST"

    for managed in "${MANAGED_DIRS[@]}"; do
        local target_dir="$target_cursor/$managed"
        [[ -d "$target_dir" ]] || continue

        while IFS= read -r target_file; do
            local rel_in_managed="${target_file#$target_cursor/}"
            local src_equivalent="$SOURCE_CURSOR/$rel_in_managed"
            if [[ ! -f "$src_equivalent" ]]; then
                stale_count=$((stale_count + 1))
                stale_files="${stale_files}  - ${rel_in_managed}\n"
            fi
        done < <(find "$target_dir" -type f ! -name '.DS_Store' | sort)
    done

    local key
    key="$(echo "$rel" | tr '/' '_')"
    echo "$new_count $changed_count $uptodate_count $stale_count" > "$TMPDIR_SYNC/counts_$key"
    printf "%s" "$new_files" > "$TMPDIR_SYNC/new_$key"
    printf "%s" "$changed_files" > "$TMPDIR_SYNC/changed_$key"
    printf "%s" "$stale_files" > "$TMPDIR_SYNC/stale_$key"
}

sync_project() {
    local rel="$1"
    local target_cursor="$SEARCH_ROOT/$rel/.cursor"
    local target_harness="$SEARCH_ROOT/$rel/.harness"

    mkdir -p "$target_harness/.archive/evals"

    # Cleanup runtime artifacts
    rm -f "$target_cursor/.DS_Store" "$target_cursor/hooks/.commit-approved"
    rm -rf "$target_cursor/hooks.bak"
    if [[ -f "$target_cursor/hooks.log" ]]; then
        local log_size
        log_size=$(wc -c < "$target_cursor/hooks.log" | tr -d ' ')
        if [[ $log_size -gt 102400 ]]; then
            tail -200 "$target_cursor/hooks.log" > "$target_cursor/hooks.log.tmp"
            mv "$target_cursor/hooks.log.tmp" "$target_cursor/hooks.log"
        fi
    fi

    while IFS= read -r src_file; do
        local target_file
        target_file="$(resolve_target_path "$src_file" "$target_cursor")"

        if [[ ! -f "$target_file" ]] || ! diff -q "$src_file" "$target_file" > /dev/null 2>&1; then
            mkdir -p "$(dirname "$target_file")"
            cp "$src_file" "$target_file"
        fi
    done < "$SOURCE_FILES_LIST"

    for managed in "${MANAGED_DIRS[@]}"; do
        local target_dir="$target_cursor/$managed"
        [[ -d "$target_dir" ]] || continue

        while IFS= read -r target_file; do
            local rel_in_managed="${target_file#$target_cursor/}"
            local src_equivalent="$SOURCE_CURSOR/$rel_in_managed"
            if [[ ! -f "$src_equivalent" ]]; then
                rm "$target_file"
            fi
        done < <(find "$target_dir" -type f ! -name '.DS_Store' | sort)

        find "$target_dir" -type d -empty -delete 2>/dev/null || true
    done
}

sync_global() {
    local global_cursor="$HOME/.cursor"
    local src_dir=""
    local file_list=""
    local src_file=""
    local rel_file=""
    local target_file=""

    echo -e "${BOLD}Syncing global files to ~/.cursor/ ...${RESET}"

    for subdir in agents skills; do
        src_dir="$SOURCE_CURSOR/$subdir"
        [[ -d "$src_dir" ]] || continue

        file_list="$TMPDIR_SYNC/global_${subdir}_files"
        find "$src_dir" -type f ! -name '.DS_Store' | sort > "$file_list"

        while IFS= read -r src_file; do
            rel_file="${src_file#$SOURCE_CURSOR/}"
            target_file="$global_cursor/$rel_file"

            if [[ ! -f "$target_file" ]]; then
                if ! $DRY_RUN; then
                    mkdir -p "$(dirname "$target_file")"
                    cp "$src_file" "$target_file"
                fi
                $VERBOSE && printf "  ${GREEN}+ %s${RESET}\n" "$rel_file"
            elif ! diff -q "$src_file" "$target_file" > /dev/null 2>&1; then
                if ! $DRY_RUN; then
                    cp "$src_file" "$target_file"
                fi
                $VERBOSE && printf "  ${YELLOW}~ %s${RESET}\n" "$rel_file"
            fi
        done < "$file_list"

        local target_dir="$global_cursor/$subdir"
        if [[ -d "$target_dir" ]]; then
            while IFS= read -r target_file; do
                rel_file="${target_file#$global_cursor/}"
                src_file="$SOURCE_CURSOR/$rel_file"
                if [[ ! -f "$src_file" ]]; then
                    if ! $DRY_RUN; then
                        rm "$target_file"
                    fi
                    $VERBOSE && printf "  ${RED}- %s${RESET}\n" "$rel_file"
                fi
            done < <(find "$target_dir" -type f ! -name '.DS_Store' | sort)

            if ! $DRY_RUN; then
                find "$target_dir" -type d -empty -delete 2>/dev/null || true
            fi
        fi
    done

    echo -e "  ${CYAN}~/.cursor/${RESET}: agents + skills synced (add/update/cleanup)"
    echo ""
}

migrate_harness() {
    echo -e "${BOLD}Migrating harness state from .cursor/ → .harness/ ...${RESET}"

    local targets_file="$TMPDIR_SYNC/migrate_targets"
    find "$SEARCH_ROOT" -maxdepth 5 -name ".cursor" -type d 2>/dev/null \
        | sort \
        | while IFS= read -r cursor_dir; do
            local project_dir
            project_dir="$(dirname "$cursor_dir")"
            [[ "$project_dir" == "$SCRIPT_DIR" ]] && continue

            local needs_migration=false
            [[ -d "$cursor_dir/harness" ]] && needs_migration=true
            [[ -f "$cursor_dir/breadcrumbs.jsonl" ]] && needs_migration=true
            [[ -f "$cursor_dir/hooks.log" ]] && needs_migration=true

            if $needs_migration; then
                echo "${project_dir#$SEARCH_ROOT/}"
            fi
        done > "$targets_file"

    local migrate_count
    migrate_count=$(wc -l < "$targets_file" | tr -d ' ')

    if [[ $migrate_count -eq 0 ]]; then
        echo -e "  ${DIM}No projects need harness migration.${RESET}"
        echo ""
        return
    fi

    echo -e "  Found ${BOLD}$migrate_count${RESET} projects with harness state in .cursor/"

    while IFS= read -r rel; do
        local cursor_dir="$SEARCH_ROOT/$rel/.cursor"
        local harness_dir="$SEARCH_ROOT/$rel/.harness"
        local moved=0

        if [[ -d "$cursor_dir/harness" ]]; then
            local file_count
            file_count=$(find "$cursor_dir/harness" -type f | wc -l | tr -d ' ')

            if ! $DRY_RUN; then
                mkdir -p "$harness_dir"
                # Move contents, preserving subdirectory structure
                find "$cursor_dir/harness" -type f | while IFS= read -r f; do
                    local rel_path="${f#$cursor_dir/harness/}"
                    mkdir -p "$(dirname "$harness_dir/$rel_path")"
                    mv "$f" "$harness_dir/$rel_path"
                done
                find "$cursor_dir/harness" -type d -empty -delete 2>/dev/null || true
                rmdir "$cursor_dir/harness" 2>/dev/null || true
            fi
            moved=$((moved + file_count))
        fi

        for loose_file in breadcrumbs.jsonl hooks.log; do
            if [[ -f "$cursor_dir/$loose_file" ]]; then
                if ! $DRY_RUN; then
                    mkdir -p "$harness_dir"
                    mv "$cursor_dir/$loose_file" "$harness_dir/$loose_file"
                fi
                moved=$((moved + 1))
            fi
        done

        local label="moved"
        $DRY_RUN && label="to move"
        printf "  ${CYAN}↳${RESET} %-50s %d files %s\n" "$rel" "$moved" "$label"
    done < "$targets_file"

    echo ""
}

migrate_schema() {
    local targets_file="$1"
    echo -e "${BOLD}Checking harness schema versions...${RESET}"

    local migrated=0
    local cleaned=0

    while IFS= read -r rel; do
        local harness_dir="$SEARCH_ROOT/$rel/.harness"
        local state_file="$harness_dir/state.json"

        # Migrate v1 (features) → v2 (tasks)
        if [[ -f "$state_file" ]]; then
            local needs_v2
            needs_v2=$(python3 -c "
import json,sys
s=json.load(open('$state_file'))
sys.exit(0 if 'features' in s and 'tasks' not in s else 1)
" 2>/dev/null && echo "yes" || echo "no")

            if [[ "$needs_v2" == "yes" ]]; then
                if ! $DRY_RUN; then
                    python3 "$SCRIPT_DIR/scripts/migrate-state-schema.py" \
                        --harness-dir "$harness_dir" > /dev/null
                fi
                printf "  ${YELLOW}↳${RESET} %-50s schema v1 → v2\n" "$rel"
                migrated=$((migrated + 1))
            fi
        fi

        # Clean up stale spec.md
        for spec_path in "$harness_dir/spec.md" "$SEARCH_ROOT/$rel/.cursor/harness/spec.md"; do
            if [[ -f "$spec_path" ]]; then
                if ! $DRY_RUN; then
                    rm "$spec_path"
                fi
                printf "  ${RED}↳${RESET} %-50s removed stale %s\n" "$rel" "$(basename "$(dirname "$spec_path")")/spec.md"
                cleaned=$((cleaned + 1))
            fi
        done
    done < "$targets_file"

    if [[ $migrated -eq 0 && $cleaned -eq 0 ]]; then
        echo -e "  ${DIM}All projects already on v2 schema, no stale files.${RESET}"
    else
        [[ $migrated -gt 0 ]] && echo -e "  Migrated ${BOLD}$migrated${RESET} project(s) to v2 schema."
        [[ $cleaned -gt 0 ]] && echo -e "  Cleaned ${BOLD}$cleaned${RESET} stale file(s)."
    fi
    echo ""
}

main() {
    migrate_harness
    sync_global

    echo -e "${BOLD}Scanning $SEARCH_ROOT for .cursor/ directories...${RESET}"

    local targets_file="$TMPDIR_SYNC/targets"
    find "$SEARCH_ROOT" -maxdepth 5 -name ".cursor" -type d 2>/dev/null \
        | sort \
        | while IFS= read -r cursor_dir; do
            local project_dir
            project_dir="$(dirname "$cursor_dir")"
            if [[ "$project_dir" != "$SCRIPT_DIR" ]]; then
                echo "${project_dir#$SEARCH_ROOT/}"
            fi
        done > "$targets_file"

    local target_count
    target_count=$(wc -l < "$targets_file" | tr -d ' ')
    echo -e "Found ${BOLD}$target_count${RESET} projects (excluding rules-skills)"
    echo ""
    echo -e "${DIM}Comparing files...${RESET}"

    local changes_file="$TMPDIR_SYNC/with_changes"
    : > "$changes_file"
    local total_new=0
    local total_changed=0
    local total_stale=0

    while IFS= read -r rel; do
        compare_project "$rel"

        local key
        key="$(echo "$rel" | tr '/' '_')"
        local counts
        counts="$(cat "$TMPDIR_SYNC/counts_$key")"
        local new_count changed_count stale_count
        new_count="$(echo "$counts" | awk '{print $1}')"
        changed_count="$(echo "$counts" | awk '{print $2}')"
        stale_count="$(echo "$counts" | awk '{print $4}')"

        if [[ $new_count -gt 0 || $changed_count -gt 0 || $stale_count -gt 0 ]]; then
            echo "$rel" >> "$changes_file"
            total_new=$((total_new + new_count))
            total_changed=$((total_changed + changed_count))
            total_stale=$((total_stale + stale_count))
        fi
    done < "$targets_file"

    local changes_count
    changes_count=$(wc -l < "$changes_file" | tr -d ' ')

    if [[ $changes_count -eq 0 ]]; then
        echo -e "\n${GREEN}All $target_count projects are up-to-date.${RESET}"
        echo ""
        migrate_schema "$targets_file"
        exit 0
    fi

    local uptodate_projects=$((target_count - changes_count))

    echo ""
    printf "  ${BOLD}%-46s %5s %9s %7s %11s${RESET}\n" "Project" "New" "Changed" "Stale" "Up-to-date"
    echo "  $(printf '%.0s─' $(seq 1 82))"

    while IFS= read -r rel; do
        local key
        key="$(echo "$rel" | tr '/' '_')"
        local counts
        counts="$(cat "$TMPDIR_SYNC/counts_$key")"
        local new_c changed_c uptodate_c stale_c
        new_c="$(echo "$counts" | awk '{print $1}')"
        changed_c="$(echo "$counts" | awk '{print $2}')"
        uptodate_c="$(echo "$counts" | awk '{print $3}')"
        stale_c="$(echo "$counts" | awk '{print $4}')"

        local new_color="" changed_color="" stale_color=""
        [[ $new_c -gt 0 ]] && new_color="$GREEN"
        [[ $changed_c -gt 0 ]] && changed_color="$YELLOW"
        [[ $stale_c -gt 0 ]] && stale_color="$RED"

        printf "  %-46s ${new_color}%5d${RESET} ${changed_color}%9d${RESET} ${stale_color}%7d${RESET} %11d\n" \
            "$rel" "$new_c" "$changed_c" "$stale_c" "$uptodate_c"

        if $VERBOSE; then
            local new_files changed_files stale_files
            new_files="$(cat "$TMPDIR_SYNC/new_$key" 2>/dev/null || true)"
            changed_files="$(cat "$TMPDIR_SYNC/changed_$key" 2>/dev/null || true)"
            stale_files="$(cat "$TMPDIR_SYNC/stale_$key" 2>/dev/null || true)"
            [[ -n "$new_files" ]] && printf "${GREEN}${new_files}${RESET}\n"
            [[ -n "$changed_files" ]] && printf "${YELLOW}${changed_files}${RESET}\n"
            [[ -n "$stale_files" ]] && printf "${RED}${stale_files}${RESET}\n"
        fi
    done < "$changes_file"

    if [[ $uptodate_projects -gt 0 ]]; then
        printf "  ${DIM}(%d projects already up-to-date)${RESET}\n" "$uptodate_projects"
    fi

    echo ""
    echo -e "  Projects to update: ${BOLD}${changes_count}${RESET}"
    echo -e "  Files to add:       ${GREEN}${total_new}${RESET}"
    echo -e "  Files to update:    ${YELLOW}${total_changed}${RESET}"
    echo -e "  Files to delete:    ${RED}${total_stale}${RESET}"
    echo ""

    if $DRY_RUN; then
        echo ""
        migrate_schema "$targets_file"
        echo -e "${DIM}Dry run — no files were changed.${RESET}"
        exit 0
    fi

    if ! $AUTO_YES; then
        read -rp "Proceed? [y/N] " answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
    fi

    echo ""
    while IFS= read -r rel; do
        local key
        key="$(echo "$rel" | tr '/' '_')"
        local counts
        counts="$(cat "$TMPDIR_SYNC/counts_$key")"
        local new_c changed_c stale_c
        new_c="$(echo "$counts" | awk '{print $1}')"
        changed_c="$(echo "$counts" | awk '{print $2}')"
        stale_c="$(echo "$counts" | awk '{print $4}')"

        sync_project "$rel"
        printf "  ${CYAN}✓${RESET} %-50s +%d ~%d -%d\n" "$rel" "$new_c" "$changed_c" "$stale_c"
    done < "$changes_file"

    echo ""
    echo -e "${GREEN}Done.${RESET} Synced ${changes_count} projects."
    echo ""

    migrate_schema "$targets_file"
}

main
