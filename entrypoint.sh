#!/bin/bash
set -e

# Display version information
VERSION=$(python -c 'from bankstatements_core.__version__ import __version__; print(__version__)' 2>/dev/null || echo "unknown")
echo "🚀 Starting Bank Statement Processor v${VERSION}..."

###############################################
# PDF Analysis Utility
###############################################
if [ -n "${ANALYZE_PDF}" ]; then
    echo "🔍 Running PDF analysis utility..."

    # Build command arguments
    CMD_ARGS="/app/input/${ANALYZE_PDF}"

    # Add output path if specified (generation mode)
    if [ -n "${OUTPUT_PATH}" ]; then
        CMD_ARGS="${CMD_ARGS} --output /app/${OUTPUT_PATH}"
    fi

    # Add template path if specified (validation mode)
    if [ -n "${TEMPLATE_PATH}" ]; then
        CMD_ARGS="${CMD_ARGS} --template /app/${TEMPLATE_PATH}"
    fi

    # Add log level
    CMD_ARGS="${CMD_ARGS} --log-level ${LOG_LEVEL:-INFO}"

    python -m bankstatements_core.commands.analyze_pdf ${CMD_ARGS}
    exit 0
fi

###############################################
# Run Python processing pipeline
###############################################
echo "🔄 Running PDF processing pipeline..."
python -m bankstatements_free.app

echo "✅ Processing complete — results saved to /app/output"

###############################################
# 3. Exit behavior control (defaults to true)
###############################################
if [ "${EXIT_AFTER_PROCESSING:-true}" = "false" ]; then
    echo "✅ Container ready for interactive use"
    echo ""
    echo "📂 Directories:"
    echo "   Input:  /app/input  (mount: ./input)"
    echo "   Output: /app/output (mount: ./output)"
    echo "   Logs:   /app/logs   (mount: ./logs)"
    echo ""
    echo "💡 To process PDFs:"
    echo "   1. Add PDFs to ./input/ folder on host"
    echo "   2. Run: docker-compose exec bank-processor python -m bankstatements_free.app"
    echo ""
    echo "📊 Check logs:"
    echo "   docker-compose logs -f bank-processor"
    echo ""
    echo "🔄 Container will stay running until stopped"
    echo "   (Set EXIT_AFTER_PROCESSING=false to keep container running)"
    echo ""
    tail -f /dev/null
else
    echo "🏁 Exiting after processing completion"
    exit 0
fi
