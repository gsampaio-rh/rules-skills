#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CURSOR="$SCRIPT_DIR/library/cursor"
HOOKS_FULL="$SCRIPT_DIR/.cursor/hooks.full.json"
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

Strategy: add new files + update changed files. Never deletes project-specific extras.

Options:
  --dry-run   Show what would change without copying
  --yes       Skip confirmation prompt
  --verbose   Show per-file diffs for changed files
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
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

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
    local new_files=""
    local changed_files=""

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

    echo "$new_count $changed_count $uptodate_count" > "$TMPDIR_SYNC/counts_$(echo "$rel" | tr '/' '_')"
    printf "%s" "$new_files" > "$TMPDIR_SYNC/new_$(echo "$rel" | tr '/' '_')"
    printf "%s" "$changed_files" > "$TMPDIR_SYNC/changed_$(echo "$rel" | tr '/' '_')"
}

sync_project() {
    local rel="$1"
    local target_cursor="$SEARCH_ROOT/$rel/.cursor"
    local target_harness="$SEARCH_ROOT/$rel/.harness"

    # Ensure .harness/ directory exists in target
    mkdir -p "$target_harness/evals" "$target_harness/audits"

    while IFS= read -r src_file; do
        local target_file
        target_file="$(resolve_target_path "$src_file" "$target_cursor")"

        if [[ ! -f "$target_file" ]] || ! diff -q "$src_file" "$target_file" > /dev/null 2>&1; then
            mkdir -p "$(dirname "$target_file")"
            cp "$src_file" "$target_file"
        fi
    done < "$SOURCE_FILES_LIST"
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
    done

    echo -e "  ${CYAN}~/.cursor/${RESET}: agents + skills synced"
    echo ""
}

main() {
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

    while IFS= read -r rel; do
        compare_project "$rel"

        local key
        key="$(echo "$rel" | tr '/' '_')"
        local counts
        counts="$(cat "$TMPDIR_SYNC/counts_$key")"
        local new_count changed_count
        new_count="$(echo "$counts" | awk '{print $1}')"
        changed_count="$(echo "$counts" | awk '{print $2}')"

        if [[ $new_count -gt 0 || $changed_count -gt 0 ]]; then
            echo "$rel" >> "$changes_file"
            total_new=$((total_new + new_count))
            total_changed=$((total_changed + changed_count))
        fi
    done < "$targets_file"

    local changes_count
    changes_count=$(wc -l < "$changes_file" | tr -d ' ')

    if [[ $changes_count -eq 0 ]]; then
        echo -e "\n${GREEN}All $target_count projects are up-to-date.${RESET}"
        exit 0
    fi

    local uptodate_projects=$((target_count - changes_count))

    echo ""
    printf "  ${BOLD}%-50s %5s %9s %11s${RESET}\n" "Project" "New" "Changed" "Up-to-date"
    echo "  $(printf '%.0s─' $(seq 1 78))"

    while IFS= read -r rel; do
        local key
        key="$(echo "$rel" | tr '/' '_')"
        local counts
        counts="$(cat "$TMPDIR_SYNC/counts_$key")"
        local new_c changed_c uptodate_c
        new_c="$(echo "$counts" | awk '{print $1}')"
        changed_c="$(echo "$counts" | awk '{print $2}')"
        uptodate_c="$(echo "$counts" | awk '{print $3}')"

        local new_color="" changed_color=""
        [[ $new_c -gt 0 ]] && new_color="$GREEN"
        [[ $changed_c -gt 0 ]] && changed_color="$YELLOW"

        printf "  %-50s ${new_color}%5d${RESET} ${changed_color}%9d${RESET} %11d\n" \
            "$rel" "$new_c" "$changed_c" "$uptodate_c"

        if $VERBOSE; then
            local new_files changed_files
            new_files="$(cat "$TMPDIR_SYNC/new_$key" 2>/dev/null || true)"
            changed_files="$(cat "$TMPDIR_SYNC/changed_$key" 2>/dev/null || true)"
            [[ -n "$new_files" ]] && printf "${GREEN}${new_files}${RESET}\n"
            [[ -n "$changed_files" ]] && printf "${YELLOW}${changed_files}${RESET}\n"
        fi
    done < "$changes_file"

    if [[ $uptodate_projects -gt 0 ]]; then
        printf "  ${DIM}(%d projects already up-to-date)${RESET}\n" "$uptodate_projects"
    fi

    echo ""
    echo -e "  Projects to update: ${BOLD}${changes_count}${RESET}"
    echo -e "  Files to add:       ${GREEN}${total_new}${RESET}"
    echo -e "  Files to update:    ${YELLOW}${total_changed}${RESET}"
    echo ""

    if $DRY_RUN; then
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
        local new_c changed_c
        new_c="$(echo "$counts" | awk '{print $1}')"
        changed_c="$(echo "$counts" | awk '{print $2}')"

        sync_project "$rel"
        printf "  ${CYAN}✓${RESET} %-50s +%d ~%d\n" "$rel" "$new_c" "$changed_c"
    done < "$changes_file"

    echo ""
    echo -e "${GREEN}Done.${RESET} Synced ${changes_count} projects."
}

main
