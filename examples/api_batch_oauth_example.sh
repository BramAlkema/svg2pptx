#!/bin/bash
# Example: Using Batch API with OAuth Slides Export
#
# This script demonstrates how to use the batch processing API
# with OAuth authentication to convert SVG files to Google Slides.
#
# Prerequisites:
# 1. API server running: uvicorn api.main:app --reload
# 2. User authenticated via API OAuth endpoints
# 3. Valid API key

set -e

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-your-api-key-here}"
USER_ID="${USER_ID:-alice}"

echo "=========================================="
echo "Batch API with OAuth Slides Export Example"
echo "=========================================="
echo ""

# Step 1: Check if user is authenticated
echo "1️⃣  Checking OAuth authentication status..."
STATUS_RESPONSE=$(curl -s -X GET "$API_URL/oauth2/status/$USER_ID" \
  -H "Authorization: Bearer $API_KEY")

echo "$STATUS_RESPONSE" | jq '.'

IS_AUTHENTICATED=$(echo "$STATUS_RESPONSE" | jq -r '.is_authenticated // false')

if [ "$IS_AUTHENTICATED" != "true" ]; then
  echo ""
  echo "❌ User $USER_ID is not authenticated"
  echo ""
  echo "To authenticate:"
  echo "  1. Start OAuth flow:"
  echo "     curl -X POST $API_URL/oauth2/start \\"
  echo "       -H 'Content-Type: application/json' \\"
  echo "       -d '{\"user_id\": \"$USER_ID\"}'"
  echo ""
  echo "  2. Visit the returned auth_url in a browser"
  echo "  3. Authorize the application"
  echo ""
  exit 1
fi

echo "✅ User $USER_ID is authenticated"
echo ""

# Step 2: Create batch job with Slides export
echo "2️⃣  Creating batch job with OAuth Slides export..."

# Sample SVG URLs
SVG_URLS='[
  "https://upload.wikimedia.org/wikipedia/commons/6/6b/Simple_Periodic_Table_Chart-en.svg",
  "https://upload.wikimedia.org/wikipedia/commons/0/02/SVG_logo.svg"
]'

BATCH_REQUEST=$(cat <<EOF
{
  "urls": $SVG_URLS,
  "drive_integration_enabled": false,
  "use_clean_slate": true,
  "user_id": "$USER_ID",
  "export_to_slides": true,
  "slides_title": "Batch API Demo - OAuth Export",
  "slides_folder_id": null
}
EOF
)

echo "Request:"
echo "$BATCH_REQUEST" | jq '.'
echo ""

BATCH_RESPONSE=$(curl -s -X POST "$API_URL/batch/jobs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "$BATCH_REQUEST")

echo "Response:"
echo "$BATCH_RESPONSE" | jq '.'

JOB_ID=$(echo "$BATCH_RESPONSE" | jq -r '.job_id')

if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
  echo "❌ Failed to create batch job"
  exit 1
fi

echo "✅ Batch job created: $JOB_ID"
echo ""

# Step 3: Poll for job status
echo "3️⃣  Polling job status (waiting for Slides export)..."

MAX_ATTEMPTS=30
ATTEMPT=0
STATUS="created"

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ] && [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ] && [ "$STATUS" != "completed_slides_export_failed" ]; do
  sleep 2
  ATTEMPT=$((ATTEMPT + 1))

  STATUS_RESPONSE=$(curl -s -X GET "$API_URL/batch/jobs/$JOB_ID" \
    -H "Authorization: Bearer $API_KEY")

  STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
  SLIDES_EXPORT_STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.slides_export_status // "not_started"')
  SLIDES_URL=$(echo "$STATUS_RESPONSE" | jq -r '.slides_url // "null"')

  echo "   [$ATTEMPT/$MAX_ATTEMPTS] Status: $STATUS | Slides Export: $SLIDES_EXPORT_STATUS"
done

echo ""
echo "Final Status:"
echo "$STATUS_RESPONSE" | jq '.'
echo ""

# Step 4: Display results
if [ "$STATUS" = "completed" ]; then
  echo "✅ Batch job completed successfully!"

  if [ "$SLIDES_URL" != "null" ]; then
    echo ""
    echo "📊 Google Slides Presentation:"
    echo "   $SLIDES_URL"
    echo ""
    echo "🎉 Your SVG files have been converted and uploaded to Google Slides!"
  else
    echo "⚠️  Warning: Job completed but no Slides URL found"
  fi
elif [ "$STATUS" = "completed_slides_export_failed" ]; then
  echo "⚠️  Conversion succeeded but Slides export failed"
  echo "   Check job trace for details:"
  echo "   curl -X GET $API_URL/batch/jobs/$JOB_ID/trace"
else
  echo "❌ Batch job failed with status: $STATUS"
fi

echo ""
echo "=========================================="

# Optional: Get trace data
echo ""
echo "📋 Trace Data (optional):"
curl -s -X GET "$API_URL/batch/jobs/$JOB_ID/trace" \
  -H "Authorization: Bearer $API_KEY" | jq '.'
