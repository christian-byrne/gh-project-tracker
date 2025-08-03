#!/bin/bash
# Clear the GitHub Issue Tracker cache

CACHE_DIR=".cache"

if [ -d "$CACHE_DIR" ]; then
    echo "🗑️  Clearing cache directory: $CACHE_DIR"
    
    # Count files before deletion
    file_count=$(find "$CACHE_DIR" -type f | wc -l)
    
    # Calculate size
    if command -v du &> /dev/null; then
        cache_size=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
        echo "   Size: $cache_size"
    fi
    
    echo "   Files: $file_count"
    
    # Remove cache directory
    rm -rf "$CACHE_DIR"
    
    echo "✅ Cache cleared successfully"
else
    echo "ℹ️  No cache directory found"
fi

# Recreate cache directory
mkdir -p "$CACHE_DIR"
echo "📁 Cache directory ready for use"