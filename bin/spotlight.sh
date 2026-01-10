#!/bin/bash

# 1. Configuration
BROWSER="xdg-open"
BROWSER_INCOGNITO="google-chrome --incognito"
FILE_MANAGER="xdg-open"

# Chrome bookmarks file location
CHROME_BOOKMARKS="$HOME/.config/google-chrome/Default/Bookmarks"

# Cloud storage and file system paths
DROPBOX_PATH="$HOME/Dropbox"
GOOGLE_DRIVE_PATHS=("$HOME/Google Drive" "$HOME/GoogleDrive")
HOME_PATH="$HOME"

# File search configuration
MAX_FILE_RESULTS=10
FILE_SEARCH_DEPTH=5

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

# Function to check if input looks like a URL
is_url() {
    local input="$1"
    # Check for common URL patterns (no spaces, contains a dot, or starts with http/https)
    if [[ "$input" =~ ^https?:// ]] || [[ "$input" =~ ^[^[:space:]]+\.[a-zA-Z]{2,}(/.*)?$ ]]; then
        return 0
    fi
    return 1
}

# Function to search for files in a directory
search_files() {
    local search_path="$1"
    local query="$2"
    local max_results="${3:-$MAX_FILE_RESULTS}"
    
    if [ ! -d "$search_path" ]; then
        return
    fi
    
    # Use find to search for files matching the query (case-insensitive)
    find "$search_path" -maxdepth "$FILE_SEARCH_DEPTH" -type f -iname "*${query}*" 2>/dev/null | head -n "$max_results"
}

# Function to get Google Drive path (handles both common naming conventions)
get_google_drive_path() {
    for path in "${GOOGLE_DRIVE_PATHS[@]}"; do
        if [ -d "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    return 1
}

# 2. Get bookmarks list
BOOKMARKS=""
if [ -f "$CHROME_BOOKMARKS" ]; then
    BOOKMARKS=$(extract_bookmarks "$CHROME_BOOKMARKS")
fi

# Prepare bookmark names for display (prefixed with 🔖), sorted alphabetically
BOOKMARK_LIST=""
if [ -n "$BOOKMARKS" ]; then
    BOOKMARK_LIST=$(echo "$BOOKMARKS" | while IFS=$'\t' read -r name url; do
        echo "🔖 $name"
    done | sort -f)
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

# Check for incognito mode prefix (!)
INCOGNITO=false
if [[ "$QUERY" == "!"* ]]; then
    INCOGNITO=true
    QUERY="${QUERY#!}"
    # Trim leading space if present
    QUERY="${QUERY# }"
fi

# Select browser based on incognito mode
if $INCOGNITO; then
    ACTIVE_BROWSER="$BROWSER_INCOGNITO"
else
    ACTIVE_BROWSER="$BROWSER"
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
        $ACTIVE_BROWSER "$URL"
    fi
    exit 0
fi

# Check if input is a direct URL
if is_url "$QUERY"; then
    # Add https:// if no protocol specified
    if [[ ! "$QUERY" =~ ^https?:// ]]; then
        QUERY="https://$QUERY"
    fi
    $ACTIVE_BROWSER "$QUERY"
    exit 0
fi

# Define Search URLs
URL_DDG="https://duckduckgo.com/?q="
URL_GOOGLE="https://www.google.com/search?q="
URL_YOUTUBE="https://www.youtube.com/results?search_query="
URL_WIKIPEDIA="https://en.wikipedia.org/wiki/Special:Search?search="
URL_GITHUB="https://github.com/search?q="
URL_STACKOVERFLOW="https://stackoverflow.com/search?q="
URL_REDDIT="https://www.reddit.com/search/?q="
URL_AMAZON="https://www.amazon.com/s?k="
URL_MAPS="https://www.google.com/maps/search/"
URL_TRANSLATE="https://translate.google.com/?sl=auto&tl=en&text="

# 5. Search Logic
if [[ "$QUERY" == "g: "* ]]; then
    # Google
    TERM=${QUERY#g: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_GOOGLE}${TERM}"

elif [[ "$QUERY" == "y: "* ]]; then
    # YouTube
    TERM=${QUERY#y: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_YOUTUBE}${TERM}"

elif [[ "$QUERY" == "w: "* ]]; then
    # Wikipedia
    TERM=${QUERY#w: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_WIKIPEDIA}${TERM}"

elif [[ "$QUERY" == "gh: "* ]]; then
    # GitHub
    TERM=${QUERY#gh: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_GITHUB}${TERM}"

elif [[ "$QUERY" == "so: "* ]]; then
    # StackOverflow
    TERM=${QUERY#so: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_STACKOVERFLOW}${TERM}"

elif [[ "$QUERY" == "r: "* ]]; then
    # Reddit
    TERM=${QUERY#r: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_REDDIT}${TERM}"

elif [[ "$QUERY" == "a: "* ]]; then
    # Amazon
    TERM=${QUERY#a: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_AMAZON}${TERM}"

elif [[ "$QUERY" == "m: "* ]]; then
    # Google Maps
    TERM=${QUERY#m: }
    TERM=${TERM// /+}
    $ACTIVE_BROWSER "${URL_MAPS}${TERM}"

elif [[ "$QUERY" == "t: "* ]]; then
    # Google Translate
    TERM=${QUERY#t: }
    # URL encode the text for translate
    TERM=$(echo "$TERM" | jq -sRr @uri)
    $ACTIVE_BROWSER "${URL_TRANSLATE}${TERM}"

elif [[ "$QUERY" == "f: "* ]]; then
    # Local file system search
    TERM=${QUERY#f: }
    TERM=$(echo "$TERM" | xargs)  # Trim whitespace
    if [ -n "$TERM" ]; then
        # Search in home directory
        RESULTS=$(search_files "$HOME_PATH" "$TERM")
        if [ -n "$RESULTS" ]; then
            # Let user select from results
            SELECTED=$(echo "$RESULTS" | wofi --dmenu --prompt "Select file..." --style "$HOME/.config/wofi/search.css" --width 600)
            if [ -n "$SELECTED" ]; then
                $FILE_MANAGER "$SELECTED"
            fi
        else
            notify-send "Spotlight Search" "No files found matching '$TERM'"
        fi
    fi

elif [[ "$QUERY" == "db: "* ]]; then
    # Dropbox search
    TERM=${QUERY#db: }
    TERM=$(echo "$TERM" | xargs)  # Trim whitespace
    if [ -n "$TERM" ] && [ -d "$DROPBOX_PATH" ]; then
        # Search in Dropbox directory
        RESULTS=$(search_files "$DROPBOX_PATH" "$TERM")
        if [ -n "$RESULTS" ]; then
            # Let user select from results
            SELECTED=$(echo "$RESULTS" | wofi --dmenu --prompt "Select file from Dropbox..." --style "$HOME/.config/wofi/search.css" --width 600)
            if [ -n "$SELECTED" ]; then
                $FILE_MANAGER "$SELECTED"
            fi
        else
            notify-send "Spotlight Search" "No files found in Dropbox matching '$TERM'"
        fi
    elif [ ! -d "$DROPBOX_PATH" ]; then
        notify-send "Spotlight Search" "Dropbox folder not found at $DROPBOX_PATH"
    fi

elif [[ "$QUERY" == "gd: "* ]]; then
    # Google Drive search
    TERM=${QUERY#gd: }
    TERM=$(echo "$TERM" | xargs)  # Trim whitespace
    if [ -n "$TERM" ]; then
        GDRIVE_PATH=$(get_google_drive_path)
        if [ $? -eq 0 ]; then
            # Search in Google Drive directory
            RESULTS=$(search_files "$GDRIVE_PATH" "$TERM")
            if [ -n "$RESULTS" ]; then
                # Let user select from results
                SELECTED=$(echo "$RESULTS" | wofi --dmenu --prompt "Select file from Google Drive..." --style "$HOME/.config/wofi/search.css" --width 600)
                if [ -n "$SELECTED" ]; then
                    $FILE_MANAGER "$SELECTED"
                fi
            else
                notify-send "Spotlight Search" "No files found in Google Drive matching '$TERM'"
            fi
        else
            notify-send "Spotlight Search" "Google Drive folder not found"
        fi
    fi

else
    # Default: DuckDuckGo
    TERM=${QUERY// /+}
    $ACTIVE_BROWSER "${URL_DDG}${TERM}"
fi