#!/bin/bash
set -euo pipefail

# 日本語と半角英数字の間に半角スペースを挿入

# OS detection for sed compatibility
OS_TYPE=$(uname -s)

# ファイルパス取得
if [ -n "${1:-}" ]; then
  file_path="$1"
else
  file_path=$(jq -r '.tool_input.file_path // empty' <<<"${CLAUDE_TOOL_INPUT:-$(cat)}")
fi

# 基本チェック
[ -z "$file_path" ] || [ ! -f "$file_path" ] || [ ! -r "$file_path" ] || [ ! -w "$file_path" ] && exit 0

# 除外リスト
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

# Unicode 文字処理: macOS では Perl を優先、 Linux では GNU sed を使用
if [[ "$OS_TYPE" == "Darwin" ]] && command -v perl >/dev/null 2>&1; then
  # macOS with Unicode issues: use Perl with proper UTF-8 handling
  LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 perl -Mutf8 -CSD -pe '
    s/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])([a-zA-Z0-9])/$1 $2/g;
    s/([a-zA-Z0-9])([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/$1 $2/g;
    s/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])(\()/$1 $2/g;
    s/(\))([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/$1 $2/g;
    s/(\))([a-zA-Z0-9])/$1 $2/g;
    s/(%)([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/$1 $2/g;
    s/([（ (\[{][^）)\]}]*[）)\]}])\s+(の|と|で|が|を|は|に)/$1$2/g;
  ' "$file_path" > "$temp_file"
else
  # GNU sed (Linux) or BSD sed with Unicode support
  sed -E \
    -e 's/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])([a-zA-Z0-9])/\1 \2/g' \
    -e 's/([a-zA-Z0-9])([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/\1 \2/g' \
    -e 's/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])(\()/\1 \2/g' \
    -e 's/(\))([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/\1 \2/g' \
    -e 's/(\))([a-zA-Z0-9])/\1 \2/g' \
    -e 's/(%)([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/\1 \2/g' \
    -e 's/([（ (\[{][^）)\]}]*[）)\]}])\s+(の|と|で|が|を|は|に)/\1\2/g' \
    "$file_path" > "$temp_file"
fi

# 除外リスト適用
if [ -f "$EXCLUSIONS_FILE" ] && command -v jq >/dev/null 2>&1; then
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    escaped="${pattern//[\[\\.^$()|*+?{]/\\&}"
    
    # OS 対応の除外処理
    if [[ "$OS_TYPE" == "Darwin" ]] && command -v perl >/dev/null 2>&1; then
      spaced=$(LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 perl -Mutf8 -CSD -pe 's/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])([a-zA-Z0-9])/$1 $2/g; s/([a-zA-Z0-9])([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/$1 $2/g' <<<"$escaped")
      LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8 perl -Mutf8 -CSD -i -pe "s/\Q$spaced\E/$pattern/g" "$temp_file"
    else
      spaced=$(sed -E 's/([ぁ-ゟァ-ヿ一-鿿㐀-䶿])([a-zA-Z0-9])/\1 \2/g; s/([a-zA-Z0-9])([ぁ-ゟァ-ヿ一-鿿㐀-䶿])/\1 \2/g' <<<"$escaped")
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