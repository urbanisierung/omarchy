#!/bin/bash

# 1. Configuration
BROWSER="xdg-open"

# Chrome bookmarks file location
CHROME_BOOKMARKS="$HOME/.config/google-chrome/Default/Bookmarks"

# Function to extract bookmarks recursively from Chrome's JSON
extract_bookmarks() {
    local bookmarks_file="$1"
    if [ -f "$bookmarks_file" ]; then
        # Use jq to recursively extract all bookmarks with name and url
        jq -r '
            def extract:
                if type == "object" then
                    if .type == "url" then
                        "\(.name)\t\(.url)"
                    elif .children then
                        .children[] | extract
                    else
                        empty
                    end
                elif type == "array" then
                    .[] | extract
                else
                    empty
                end;
            .roots | to_entries[] | .value | extract
        ' "$bookmarks_file" 2>/dev/null
    fi
}

# 2. Get bookmarks list
BOOKMARKS=""
if [ -f "$CHROME_BOOKMARKS" ]; then
    BOOKMARKS=$(extract_bookmarks "$CHROME_BOOKMARKS")
fi

# Prepare bookmark names for display (prefixed with 🔖)
BOOKMARK_LIST=""
if [ -n "$BOOKMARKS" ]; then
    BOOKMARK_LIST=$(echo "$BOOKMARKS" | while IFS=$'\t' read -r name url; do
        echo "🔖 $name"
    done)
fi

# 3. Launch Wofi in dmenu mode
# - dmenu: reads from stdin (bookmarks list)
# - prompt: sets the text
# - style: path to our custom CSS
QUERY=$(echo "$BOOKMARK_LIST" | wofi --dmenu --prompt "Search / Bookmarks..." --style "$HOME/.config/wofi/search.css" --width 600)

# 4. Process the Input
# If the user cancelled (pressed Escape), exit
if [ -z "$QUERY" ]; then
    exit 0
fi

# Check if user selected a bookmark (starts with 🔖)
if [[ "$QUERY" == "🔖 "* ]]; then
    # Extract the bookmark name (remove the prefix)
    BOOKMARK_NAME="${QUERY#🔖 }"
    # Find the URL for this bookmark
    URL=$(echo "$BOOKMARKS" | while IFS=$'\t' read -r name url; do
        if [ "$name" = "$BOOKMARK_NAME" ]; then
            echo "$url"
            break
        fi
    done)
    if [ -n "$URL" ]; then
        $BROWSER "$URL"
    fi
    exit 0
fi

# Define Search URLs
URL_DDG="https://duckduckgo.com/?q="
URL_GOOGLE="https://www.google.com/search?q="
URL_YOUTUBE="https://www.youtube.com/results?search_query="

# 5. Search Logic
if [[ "$QUERY" == "g: "* ]]; then
    # Strip prefix and search Google
    TERM=${QUERY#g: }
    # Encode spaces (basic)
    TERM=${TERM// /+}
    $BROWSER "${URL_GOOGLE}${TERM}"

elif [[ "$QUERY" == "y: "* ]]; then
    # Strip prefix and search YouTube
    TERM=${QUERY#y: }
    TERM=${TERM// /+}
    $BROWSER "${URL_YOUTUBE}${TERM}"

else
    # Default: DuckDuckGo
    TERM=${QUERY// /+}
    $BROWSER "${URL_DDG}${TERM}"
fi