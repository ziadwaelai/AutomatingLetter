# Quick Start: Email Mappings Setup

## 🚀 5-Minute Setup Guide

This guide will help you enable gmail/yahoo users in your system.

---

## Step 1: Create EmailMappings Worksheet (2 minutes)

1. **Open your Master Sheet**:
   ```
   https://docs.google.com/spreadsheets/d/11eCtNuW4cl03TX0G20alx3_6B5DI7IbpQPnPDeRGKlI
   ```

2. **Add a new worksheet**:
   - Click the "+" button at the bottom
   - Name it exactly: **EmailMappings** (case-sensitive!)

3. **Add these headers in Row 1**:
   ```
   email | sheetId | GoogleDriveId | displayName | letterTemplate | letterType
   ```

---

## Step 2: Create a Client Sheet for Gmail Users (1 minute)

1. **Create a new Google Sheet**
   - Go to: https://sheets.new
   - Name it: "Freelancer Team Sheet" (or any name)

2. **Add three worksheets** (rename existing ones):
   - **Users**
   - **Templates**
   - **Instructions**

3. **Copy the Sheet ID**:
   - Look at the URL: `https://docs.google.com/spreadsheets/d/[THIS_IS_THE_SHEET_ID]/edit`
   - Copy the long ID (e.g., `1AbCdEfGhIjKlMnOpQrStUvWxYz123456789`)

---

## Step 3: Add Email Mapping (30 seconds)

Back in your **Master Sheet → EmailMappings** worksheet:

**Add this row**:
```
| email              | sheetId                  | GoogleDriveId | displayName     | letterTemplate | letterType |
|--------------------|--------------------------|---------------|-----------------|----------------|------------|
| alice@gmail.com    | [PASTE_YOUR_SHEET_ID]   | drv_001       | Freelancer Team | default        | formal     |
```

**Replace `[PASTE_YOUR_SHEET_ID]`** with the Sheet ID you copied!

---

## Step 4: Add User to Client Sheet (1 minute)

In your **new sheet → Users** worksheet:

**Add headers in Row 1**:
```
email | full_name | PhoneNumber | role | status | created_at | password
```

**Add user in Row 2**:
```
| email           | full_name   | PhoneNumber | role  | status | created_at          | password  |
|-----------------|-------------|-------------|-------|--------|---------------------|-----------|
| alice@gmail.com | Alice Smith | +966123...  | admin | active | 2025-01-15T10:00:00 | [LEAVE_EMPTY] |
```

**Note**: Leave password empty for now - user will set it during first registration.

---

## Step 5: Test It! (30 seconds)

### Option A: Using curl

```bash
curl -X POST http://localhost:5000/api/v1/user/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@gmail.com",
    "password": "SecurePass123!",
    "full_name": "Alice Smith"
  }'
```

### Option B: Using Postman/Insomnia

```
POST http://localhost:5000/api/v1/user/create-user

Body (JSON):
{
  "email": "alice@gmail.com",
  "password": "SecurePass123!",
  "full_name": "Alice Smith"
}
```

---

## ✅ Verification

You should see:
```json
{
  "success": true,
  "message": "User created successfully",
  "user": {
    "email": "alice@gmail.com",
    "full_name": "Alice Smith",
    "role": "user",
    "status": "inactive"
  },
  "client": {
    "client_id": "EMAIL-MAP-alice",
    "display_name": "Freelancer Team",
    "sheet_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz123456789"
  }
}
```

---

## 🎉 Success!

Now you can:
- ✅ Login with `alice@gmail.com`
- ✅ Add more gmail users to the same sheet
- ✅ Existing domain-based users still work!

---

## Adding More Users

### Same Team (Share Same Sheet)

Add to **EmailMappings**:
```
bob@yahoo.com | [SAME_SHEET_ID] | drv_001 | Freelancer Team | default | formal
```

Add to **Users worksheet** (in client sheet):
```
bob@yahoo.com | Bob Jones | +966456... | user | active | 2025-01-16T10:00:00 | [EMPTY]
```

### Different Team (New Sheet)

1. Create a new Google Sheet
2. Copy new Sheet ID
3. Add new row in EmailMappings with new Sheet ID
4. Add user in new sheet's Users worksheet

---

## Troubleshooting

### ❌ "No client found for this email domain"

**Solution**: Check that:
1. EmailMappings worksheet exists
2. Email is spelled correctly in EmailMappings
3. sheetId is correct

### ❌ "User not found in client sheet"

**Solution**: Check that:
1. User exists in the client sheet's Users worksheet
2. Email matches exactly (case-insensitive)
3. Status is "active"

### ❌ "EmailMappings worksheet not found"

**Solution**:
1. Worksheet name must be exactly "EmailMappings" (capital E, capital M)
2. It must be in the Master Sheet, not the client sheet

---

## Next Steps

- 📖 Read full documentation: [EMAIL_MAPPINGS_FEATURE.md](EMAIL_MAPPINGS_FEATURE.md)
- 🔐 Review security: Set strong passwords
- 👥 Add more team members
- 🎨 Customize templates in client sheet

---

**Need help?** Check the full documentation or open an issue.
