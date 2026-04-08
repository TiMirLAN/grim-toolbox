#!/bin/bash
set -e

REPO_DIR="${REPO_DIR:-$(pwd)}"
PREV_TAG="${PREV_TAG:-}"
NEW_TAG="HEAD"
OUTPUT_FILE="${OUTPUT_FILE:-CHANGELOG.md}"

echo "Fetching latest tags..."
git fetch --tags --force 2>/dev/null || true

if [ -z "$PREV_TAG" ]; then
    PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    
    if [ -z "$PREV_TAG" ]; then
        PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null | head -1 || echo "")
    fi
    
    if [ -z "$PREV_TAG" ]; then
        echo "Error: No previous tag found"
        exit 1
    fi
fi

echo "Generating changelog from $PREV_TAG to current state (HEAD)..."

DIFF_FILE=$(mktemp /tmp/extip-rust-diff.XXXXXX)
git diff "$PREV_TAG..HEAD" -- apps/extip-rust/ > "$DIFF_FILE"

COMMIT_LIST=$(git log "$PREV_TAG..HEAD" --oneline -- apps/extip-rust/ 2>/dev/null | head -20 || echo "")

if [ -z "$COMMIT_LIST" ]; then
    echo "No commits found between $PREV_TAG and HEAD"
    echo "Current state is same as $PREV_TAG"
    rm -f "$DIFF_FILE"
    exit 0
fi

{
    echo "Analyze commits and create a changelog."
    echo ""
    echo "Repository uses custom commit notation:"
    echo "- + = new features (additions)"
    echo "- ~ = changes/refactoring"
    echo "- ! = bug fixes"
    echo ""
    echo "Commits since $PREV_TAG:"
    echo "$COMMIT_LIST"
    echo ""
    echo "Create a changelog in markdown format:"
    echo "## 🚀 Features"
    echo "- item 1"
    echo "## ♻️ Changes"
    echo "- item 1"
    echo "## 🐛 Bug Fixes"
    echo "- item 1"
    echo ""
    echo "Focus on user-visible changes. Be concise (under 50 chars per bullet)."
} | opencode run \
    --dir "$REPO_DIR" \
    --print-logs \
    "Generate changelog from the commits list above." \
    > /tmp/opencode-output.txt 2>&1

grep -E "^## |^- " /tmp/opencode-output.txt | head -50 > "$OUTPUT_FILE" || {
    echo "## 🚀 Features" >> "$OUTPUT_FILE"
    echo "## ♻️ Changes" >> "$OUTPUT_FILE"
    echo "## 🐛 Bug Fixes" >> "$OUTPUT_FILE"
}

rm -f "$DIFF_FILE"

echo ""
echo "Changelog saved to $OUTPUT_FILE"
echo "From: $PREV_TAG -> HEAD"