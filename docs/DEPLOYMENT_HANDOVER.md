# Deployment Handover - Automating Letter System

---

## What You Need

### Server Requirements
- Ubuntu 20.04+ Linux server
- Python 3.8+
- 2GB RAM, 20GB disk

### Credentials Required
- OpenAI API key
- Google service account JSON file
- SSL certificates (cert.pem + key.pem)
- Twilio credentials (for WhatsApp)

---

## Part 1: Backend Setup

### Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3 python3-pip python3-venv git

# Install Playwright dependencies
sudo apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2
```

### Step 2: Setup Application

```bash
# Create user
sudo useradd -m -s /bin/bash shobbak
sudo su - shobbak

# Clone and setup
cd ~
git clone https://github.com/ziadwaelai/AutomatingLetter
cd AutomatingLetter

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
playwright install chromium

```

### Step 3: Configure Environment

```bash
# Create .env file
nano .env
```

**Add these variables:**
```bash
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
GOOGLE_DRIVE_FOLDER_ID=YOUR_FOLDER_ID

# Optional
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_YOUR_KEY
```

### Step 4: Add Credentials

```bash
# Upload service account JSON
# Copy to: /home/shobbak/AutomatingLetter/automating-letter-creations.json
chmod 600 automating-letter-creations.json

# Add SSL certificates
# Copy cert.pem and key.pem to project directory
chmod 600 cert.pem key.pem
```

### Step 5: Create Systemd Service

```bash
sudo nano /etc/systemd/system/automating-letter.service
```

**Paste this:**
```ini
[Unit]
Description=Automating Letter Flask App
After=network.target

[Service]
User=shobbak
WorkingDirectory=/home/shobbak/AutomatingLetter
ExecStart=/home/shobbak/AutomatingLetter/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --certfile=/home/shobbak/AutomatingLetter/cert.pem --keyfile=/home/shobbak/AutomatingLetter/key.pem app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### Step 6: Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable automating-letter
sudo systemctl start automating-letter
sudo systemctl status automating-letter

# Allow firewall
sudo ufw allow 5000/tcp

# Test
curl -k https://localhost:5000/health
```

---

## Part 2: n8n WhatsApp Setup

### Step 1: Create n8n Account

1. Go to https://n8n.io
2. Sign up for cloud account
3. Login to dashboard

### Step 2: Import Workflow

1. Download workflow file: `n8n-whatsapp-workflow.json`
2. In n8n: **Workflows** → **Import from File**
3. Select file and click Import

### Step 3: Configure n8n Settings

#### A. Get Webhook URL
1. Click on **Webhook** node in workflow
2. Copy **Production URL** (example: `https://your-account.app.n8n.cloud/webhook/send`)

#### B. Update Backend with n8n URL
```bash
ssh YOUR_SERVER_IP
cd ~/AutomatingLetter
nano src/api/whatsapp_routes.py

# Find line 137 and update:
webhook_url = "https://your-account.app.n8n.cloud/webhook/send"

# Save and restart
sudo systemctl restart automating-letter
```

#### C. Configure n8n Environment Variables

In n8n workflow settings, add these environment variables:

```bash
# Backend API endpoint
BACKEND_HOST=https://YOUR_SERVER_IP:5000

# Alternative if using custom domain
BACKEND_HOST=https://api.yourdomain.com
```

### Step 4: Setup Twilio WhatsApp

#### A. Get Twilio Credentials

1. Go to https://www.twilio.com/console
2. Get your credentials:
   - Account SID
   - Auth Token
   - WhatsApp Phone Number (format: whatsapp:+14155238886)

#### B. Add Credentials to n8n

1. In n8n workflow, click on **Twilio** or **WhatsApp** node
2. Click **Create New Credentials**
3. Add:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: `your_auth_token`
   - **Phone Number**: `whatsapp:+14155238886`
4. Save credentials

### Step 5: Activate Workflow

1. Toggle workflow to **Active**
2. Verify webhook is listening
3. Test the connection

### Step 6: Test Integration

```bash
# Test webhook
curl -X POST https://your-account.app.n8n.cloud/webhook/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "whatsapp:+201234567890",
    "name": "Test User",
    "letter_id": "TEST123",
    "letter_data": {"Title": "Test", "Letter": "Content"}
  }'

# Test via API
curl -k -X POST https://YOUR_SERVER_IP:5000/api/v1/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "201234567890",
    "letter_id": "251214-12345"
  }'
```

---

## Part 3: Google Setup

### Google Sheets

**Spreadsheet Name:** "AI Letter Generating"

**Share with service account:**
1. Open Google Sheets
2. Click **Share**
3. Add email from `automating-letter-creations.json` (find `client_email`)
4. Give **Editor** permission

**Required Worksheets:**
- Submissions: `Timestamp | Type of Letter | Recipient | Title | First Time? | Content | URL | Revision | ID | Username`
- WhatApp: `Name | Number | Letter_Id | Title | Sign`
- Instructions: `Category | Instruction`
- Ideal: `Category | Letter`
- Poc: `Member Name | Member Info`
- Intro: `Intro Text`

### Google Drive

1. Create folder for letters
2. Share with service account email (Editor permission)
3. Copy folder ID from URL
4. Add to `.env`: `GOOGLE_DRIVE_FOLDER_ID=FOLDER_ID_HERE`

---

## Verification

### Check Backend
```bash
sudo systemctl status automating-letter
curl -k https://YOUR_SERVER_IP:5000/health
curl -k https://YOUR_SERVER_IP:5000/api/v1/whatsapp/users
```

### Check n8n
- Open n8n dashboard
- Go to **Executions** tab
- Click **Execute Workflow** to test
- Verify WhatsApp message sent

### Check Logs
```bash
tail -f /home/shobbak/AutomatingLetter/logs/app.log
sudo journalctl -u automating-letter -f
```

---

## Common Issues

### Service Won't Start
```bash
sudo journalctl -u automating-letter -n 50
sudo systemctl restart automating-letter
```

### Google Sheets Error
```bash
ls -la automating-letter-creations.json
chmod 600 automating-letter-creations.json
# Verify sheet is shared with service account
```

### OpenAI Error
```bash
cat .env | grep OPENAI_API_KEY
# Check quota at: https://platform.openai.com/usage
```

### WhatsApp Not Sending
```bash
# Check n8n execution logs
# Verify Twilio credentials
# Test webhook URL
tail -f logs/app.log | grep -i whatsapp
```

---

## Quick Commands

```bash
# Restart service
sudo systemctl restart automating-letter

# View logs
tail -f logs/app.log

# Update code
cd ~/AutomatingLetter
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart automating-letter

# Test health
curl -k https://localhost:5000/health
```

---

## Configuration Summary

### Backend
- **Server:** YOUR_SERVER_IP:5000
- **User:** shobbak
- **Service:** automating-letter.service

### n8n
- **URL:** https://your-account.app.n8n.cloud
- **Webhook:** /webhook/send
- **Env Vars:** BACKEND_HOST

### Twilio
- **Console:** https://www.twilio.com/console
- **Credentials:** Account SID, Auth Token, Phone Number

### Google
- **Sheets:** "AI Letter Generating"
- **Drive Folder:** YOUR_FOLDER_ID

---

