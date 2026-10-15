# MFA reels: Google Sheet -> GitHub -> Make (3 ops/post) -> Instagram
Sheet "MFA Reels": No. | Text | Status | Video URL | Caption. Add rows with Status READY.
Every hour GitHub reads the sheet CSV, renders new READY rows to videos/, posts the OLDEST unposted one via the Make webhook.
Make (one scenario, 3 operations): webhook -> Instagram reel -> sheet Status POSTED (FAILED on error).
Secrets: SHEET_CSV_URL, POST_URL. posted.txt prevents double posts. Test: python3 render.py "Text" out.mp4
