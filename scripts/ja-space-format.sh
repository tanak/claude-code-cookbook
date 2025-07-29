#!/bin/bash
set -euo pipefail

# æ¥æ¬èªã¨åè§è±æ°å­ã®éã«åè§ã¹ãã¼ã¹ãæ¿å¥

# OS detection for sed compatibility
OS_TYPE=$(uname -s)

# ãã¡ã¤ã«ãã¹åå¾
if [ -n "${1:-}" ]; then
  file_path="$1"
else
  file_path=$(jq -r '.tool_input.file_path // empty' <<<"${CLAUDE_TOOL_INPUT:-$(cat)}")
fi

# åºæ¬ãã§ãã¯
[ -z "$file_path" ] || [ ! -f "$file_path" ] || [ ! -r "$file_path" ] || [ ! -w "$file_path" ] && exit 0

# é¤å¤ãªã¹ã
EXCLUSIONS_FILE="$(dirname "${BASH_SOURCE[0]}")/ja-space-exclusions.json"

# OS-compatible temporary file creation
case "$OS_TYPE" in
  Darwin|*BSD)
    temp_file=$(mktemp -t ja-space-format.XXXXXX)
    ;;
  *)
    temp_file=$(mktemp)
    ;;
esac
trap 'rm -f "$temp_file"' EXIT

# Unicode æå­å¦ç: macOS ã§ã¯ Perl ãåªåã Linux ã§ã¯ GNU sed ãä½¿ç¨
if [[ "$OS_TYPE" == "Darwin" ]] && command -v perl >/dev/null 2>&1; then
  # macOS with Unicode issues: use Perl
  perl -CIO -pe '
    s/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])([a-zA-Z0-9])/$1 $2/g;
    s/([a-zA-Z0-9])([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/$1 $2/g;
    s/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])(\()/$1 $2/g;
    s/(\))([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/$1 $2/g;
    s/(\))([a-zA-Z0-9])/$1 $2/g;
    s/(%)([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/$1 $2/g;
    s/([ï¼ (\[{][^ï¼)\]}]*[ï¼)\]}])\s+(ã®|ã¨|ã§|ã|ã|ã¯|ã«)/$1$2/g;
  ' "$file_path" > "$temp_file"
else
  # GNU sed (Linux) or BSD sed with Unicode support
  sed -E \
    -e 's/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])([a-zA-Z0-9])/\1 \2/g' \
    -e 's/([a-zA-Z0-9])([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/\1 \2/g' \
    -e 's/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])(\()/\1 \2/g' \
    -e 's/(\))([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/\1 \2/g' \
    -e 's/(\))([a-zA-Z0-9])/\1 \2/g' \
    -e 's/(%)([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/\1 \2/g' \
    -e 's/([ï¼ (\[{][^ï¼)\]}]*[ï¼)\]}])\s+(ã®|ã¨|ã§|ã|ã|ã¯|ã«)/\1\2/g' \
    "$file_path" > "$temp_file"
fi

# é¤å¤ãªã¹ãé©ç¨
if [ -f "$EXCLUSIONS_FILE" ] && command -v jq >/dev/null 2>&1; then
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    escaped="${pattern//[\[\\.^$()|*+?{]/\\&}"
    
    # OS å¯¾å¿ã®é¤å¤å¦ç
    if [[ "$OS_TYPE" == "Darwin" ]] && command -v perl >/dev/null 2>&1; then
      spaced=$(perl -CIO -pe 's/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])([a-zA-Z0-9])/$1 $2/g; s/([a-zA-Z0-9])([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/$1 $2/g' <<<"$escaped")
      perl -CIO -i -pe "s/\Q$spaced\E/$pattern/g" "$temp_file"
    else
      spaced=$(sed -E 's/([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])([a-zA-Z0-9])/\1 \2/g; s/([a-zA-Z0-9])([ã-ãã¡-ã¿ä¸-é¿¿ã-ä¶¿])/\1 \2/g' <<<"$escaped")
      case "$OS_TYPE" in
        Darwin|*BSD)
          sed -i '' "s/$spaced/$pattern/g" "$temp_file"
          ;;
        *)
          sed -i "s/$spaced/$pattern/g" "$temp_file"
          ;;
      esac
    fi
  done < <(jq -r '.exclusions[]' "$EXCLUSIONS_FILE" 2>/dev/null)
fi

mv "$temp_file" "$file_path"