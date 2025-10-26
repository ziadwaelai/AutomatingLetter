# Implementation Checklist: Google Drive Folder ID Integration

## Pre-Deployment Checklist

### Master Sheet Setup

- [ ] Master sheet has the following columns:
  - [ ] `clientId`
  - [ ] `displayName`
  - [ ] `primaryDomain`
  - [ ] `extraDomains`
  - [ ] `sheetId`
  - [ ] `GoogleDriveId` ← **CRITICAL**

- [ ] `GoogleDriveId` column contains valid Google Drive folder IDs
  - [ ] Format: `1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P` (from folder URL)
  - [ ] All rows have folder IDs populated
  - [ ] No empty cells in GoogleDriveId column

### Google Drive Configuration

- [ ] Each client has a dedicated Google Drive folder created
- [ ] Folder IDs added to master sheet:
  - Client 1: `[Folder ID 1]`
  - Client 2: `[Folder ID 2]`
  - Client N: `[Folder ID N]`

- [ ] Service account has **Editor** access to all folders
  - [ ] Service account email obtained from `automating-letter-creations.json`
  - [ ] Each folder shared with service account
  - [ ] Permission level: Editor (not Viewer or Commenter)

- [ ] Google Drive API enabled in Google Cloud Console
  - [ ] Project verified
  - [ ] API quotas checked

### Code Deployment

- [ ] All 3 modified files deployed:
  - [ ] `src/services/user_management_service.py`
  - [ ] `src/api/archive_routes.py`
  - [ ] `src/services/drive_logger.py`

- [ ] No compilation errors:
  ```bash
  python -m py_compile src/services/user_management_service.py
  python -m py_compile src/api/archive_routes.py
  python -m py_compile src/services/drive_logger.py
  ```

- [ ] Application restarts successfully
  ```bash
  python app.py
  ```

## Functional Testing

### Test 1: JWT Token Contains google_drive_id

**Test Steps**:
```bash
# 1. Login with user credentials
curl -X POST http://localhost:5000/api/v1/user/validate \
  -H "Content-Type: application/json" \
  -d '{"email": "user@client.com", "password": "password"}'

# 2. Get JWT token from response

# 3. Decode JWT to verify google_drive_id
python -c "
import jwt
import sys

token = sys.argv[1]
decoded = jwt.decode(token, options={'verify_signature': False})
print(f'google_drive_id: {decoded.get(\"google_drive_id\", \"NOT FOUND\")}')
print(f'sheet_id: {decoded.get(\"sheet_id\", \"NOT FOUND\")}')
" <token_here>

# Expected output:
# google_drive_id: 1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P
# sheet_id: [Sheet ID]
```

- [ ] JWT contains `google_drive_id`
- [ ] JWT contains `sheet_id`
- [ ] Both IDs match master sheet

**Expected Result**: ✅ PASS

### Test 2: Missing google_drive_id Error

**Setup**: Remove `GoogleDriveId` from master sheet (temporarily)

**Test Steps**:
```bash
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "letter_content": "Test",
    "letter_type": "General",
    "recipient": "Test",
    "title": "Test",
    "is_first": true,
    "ID": "TEST-001"
  }'
```

**Expected Result**:
```json
{
  "error": "معرف مجلد Google Drive غير موجود في التوكن",
  "status": "error"
}
```

- [ ] HTTP 400 returned
- [ ] Error message in Arabic

**Action**: Restore `GoogleDriveId` to master sheet

### Test 3: Successful Letter Archive

**Test Steps**:
```bash
# Archive a letter
curl -X POST http://localhost:5000/api/v1/archive/letter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{
    "letter_content": "This is a test letter content",
    "letter_type": "General Inquiry",
    "recipient": "John Doe",
    "title": "Test Letter",
    "is_first": true,
    "ID": "TEST-20251022-001"
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Letter archiving started for ID: TEST-20251022-001",
  "processing": "background",
  "letter_id": "TEST-20251022-001"
}
```

- [ ] HTTP 200 returned
- [ ] Background processing started

**Verify in Google Drive**:
- [ ] Open client's Google Drive folder
- [ ] Look for file: `Test Letter_TEST-20251022-001.pdf`
- [ ] File exists and is readable
- [ ] File NOT in shared/default folder (isolation verified)

**Verify in Google Sheet**:
- [ ] Open client's Google Sheet (from master sheet `sheetId`)
- [ ] Navigate to "Submissions" sheet
- [ ] New row added with:
  - [ ] `ID`: TEST-20251022-001
  - [ ] `Timestamp`: Current date/time
  - [ ] `Created_by`: user@client.com
  - [ ] `Letter_type`: General Inquiry
  - [ ] `Recipient_name`: John Doe
  - [ ] `Subject`: Test Letter
  - [ ] `Final_letter_url`: [Google Drive link]

### Test 4: Multiple Clients Isolation

**Test Steps** (if multiple clients available):

```bash
# Create file for Client 1
# Login as user1@client1.com, archive letter TEST-CLIENT1-001

# Create file for Client 2
# Login as user2@client2.com, archive letter TEST-CLIENT2-001
```

**Expected Result**:
- [ ] Client 1's Drive folder contains: `Test Letter_TEST-CLIENT1-001.pdf`
- [ ] Client 2's Drive folder contains: `Test Letter_TEST-CLIENT2-001.pdf`
- [ ] No files in wrong folders
- [ ] Each client can only see their own letters

## Monitoring & Logging

### Log Verification

**Check application logs for**:

```
✅ Successful:
INFO: Archive request from user: user@client.com, client: client_001, sheet: sheet_123, drive: folder_456
INFO: Starting background archiving for letter ID: TEST-20251022-001 (sheet: sheet_123, drive: folder_456)
INFO: File uploaded to Drive: Test Letter_TEST-20251022-001.pdf (ID: file_id_xyz)
INFO: Successfully archived letter TEST-20251022-001 to Drive and logged to sheet sheet_123

❌ Error:
ERROR: folder_id (google_drive_id from JWT token) is required for Drive upload
```

- [ ] Check logs for successful uploads
- [ ] No warnings about missing folder IDs
- [ ] No fallback to environment variable

### Performance Check

```bash
# Monitor archive performance
# Expected time: 5-15 seconds (background processing)

# Check Google Drive upload speed
# Expected: 1-5 seconds per 1MB PDF

# Check Sheet logging
# Expected: 2-5 seconds
```

- [ ] Archive completes within acceptable time
- [ ] No timeout errors
- [ ] No API rate limit errors

## Rollback Plan

If issues occur:

### Option 1: Quick Rollback

```bash
# Restore previous code versions
git checkout HEAD~1 -- src/services/user_management_service.py
git checkout HEAD~1 -- src/api/archive_routes.py
git checkout HEAD~1 -- src/services/drive_logger.py

# Restart application
python app.py
```

- [ ] Previous code deployed
- [ ] Application running
- [ ] Test with old code

### Option 2: Partial Rollback

If only Drive upload failing:
- [ ] Add `GOOGLE_DRIVE_FOLDER_ID` back to environment
- [ ] Modify `drive_logger.py` to use env var as fallback
- [ ] Keep JWT token changes (safe)

### Option 3: Database Cleanup

If corrupt data needs cleanup:
```python
# Remove test entries from sheet
# DELETE rows where ID LIKE 'TEST-%'
```

- [ ] Remove test letters from Drive folders
- [ ] Remove test entries from Google Sheets

## Success Criteria

**Deployment is SUCCESSFUL if**:

✅ All tests pass:
- [ ] JWT token includes google_drive_id
- [ ] Missing folder_id returns 400 error
- [ ] Letters archive to correct client folder
- [ ] Letters NOT in shared folder
- [ ] Letters logged to correct sheet
- [ ] Multiple clients isolated properly

✅ No errors in logs:
- [ ] No "GOOGLE_DRIVE_FOLDER_ID not set" warnings
- [ ] No Drive upload failures
- [ ] No Sheet logging errors

✅ Performance acceptable:
- [ ] Archive completes in <30 seconds
- [ ] Drive upload in <5 seconds
- [ ] No rate limiting

**If ANY test fails**: DO NOT consider deployment successful, review logs and troubleshoot

## Troubleshooting Guide

### Issue: google_drive_id not in JWT token

**Check**:
1. Master sheet has `GoogleDriveId` column
2. Column spelled correctly (case-sensitive)
3. All rows have folder IDs
4. Application restarted after deployment

**Fix**:
```python
# Verify master sheet lookup
from src.services.user_management_service import get_user_management_service
service = get_user_management_service()
client_info = service.get_client_info_by_email("user@domain.com")
print(f"google_drive_id: {client_info.google_drive_id}")
```

### Issue: 400 Error - "معرف مجلد Google Drive غير موجود في التوكن"

**Check**:
1. User logged in to get new JWT token (old tokens won't have google_drive_id)
2. Master sheet updated with folder IDs
3. Application restarted

**Fix**:
1. Clear old JWT tokens
2. Re-login to get new token with google_drive_id
3. Retry archive

### Issue: Files not appearing in Google Drive

**Check**:
1. Service account has Editor access to folder
2. Folder ID is correct
3. Google Drive API quotas not exceeded
4. Check logs for upload errors

**Fix**:
```bash
# Verify service account access
# Go to folder → Share → Check service account email listed

# Test Drive API access
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file(
    'automating-letter-creations.json',
    scopes=['https://www.googleapis.com/auth/drive']
)
drive = build('drive', 'v3', credentials=creds)
folder = drive.files().get(fileId='FOLDER_ID').execute()
print(f'Folder: {folder[\"name\"]}')
"
```

### Issue: Letters in wrong folder

**Check**:
1. Different clients have different JWT tokens
2. Each JWT has correct google_drive_id for that client
3. Master sheet rows mapped correctly

**Fix**:
1. Verify master sheet mapping
2. Check JWT token for each user
3. Manually move misplaced files for now
4. Retry with correct configuration

## Post-Deployment Monitoring

**First 24 Hours**:
- [ ] Monitor application logs
- [ ] Check Google Drive for correct file placement
- [ ] Verify Sheet logging working
- [ ] Monitor API usage and quotas

**First Week**:
- [ ] Monitor for any intermittent failures
- [ ] Check error logs daily
- [ ] Verify all clients' folders have files
- [ ] Performance metrics acceptable

**Ongoing**:
- [ ] Weekly audit of folder structure
- [ ] Monthly quota review
- [ ] Regular backups of master sheet

---

## Sign-Off

**Deployment Date**: _______________
**Deployed By**: _______________
**Verified By**: _______________

**All Tests Passed**: [ ] Yes [ ] No

**Issues Encountered**: _______________________________________________

**Notes**: _________________________________________________________

---

**Status**: Ready for deployment ✅
