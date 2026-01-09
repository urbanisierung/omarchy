#!/bin/bash

# 1. Configuration
# You can add more prefixes here later
BROWSER="xdg-open" 

# 2. Launch Wofi in dmenu mode
# - dmenu: reads from stdin (we give it nothing)
# - prompt: sets the text
# - lines 0: hides the list so it looks like a search bar
# - style: path to our custom CSS
QUERY=$(echo "" | wofi --dmenu --lines 0 --prompt "Search Web..." --style "$HOME/.config/wofi/search.css" --width 600)

# 3. Process the Input
# If the user cancelled (pressed Escape), exit
if [ -z "$QUERY" ]; then
    exit 0
fi

# Define Search URLs
URL_DDG="https://duckduckgo.com/?q="
URL_GOOGLE="https://www.google.com/search?q="
URL_YOUTUBE="https://www.youtube.com/results?search_query="

# 4. Logic
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