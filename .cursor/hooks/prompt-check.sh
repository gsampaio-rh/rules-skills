#!/bin/bash
# Lightweight prompt quality nudge for beforeSubmitPrompt hook.
# Reads the user's prompt from stdin JSON, checks for very short or
# unstructured prompts, and prepends a gentle context reminder.

input=$(cat)
prompt=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', data.get('content', '')))
except:
    print('')
" 2>/dev/null)

length=${#prompt}

if [ "$length" -lt 30 ] && [ "$length" -gt 0 ]; then
    echo '{
        "addToPrompt": "[Prompt quality reminder: For better results, include what you want changed, which files are involved, and how to verify the result.]"
    }'
    exit 0
fi

echo '{}'
exit 0
