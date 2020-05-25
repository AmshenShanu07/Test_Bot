curl -F chat_id="-1001151133686" -F text="$(./changelog.sh)" -F parse_mode="HTML" https://api.telegram.org/bot$BOT_TOKEN/sendMessage
