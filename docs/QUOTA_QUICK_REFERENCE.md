# Quick Reference: Quota Enforcement

## Setup in 3 Steps

### Step 1: Create Settings Sheet
In your Google Sheet, add a sheet called "Settings"

### Step 2: Add Quota Row
```
key           | value
quota_month   | 100
```

### Step 3: Done!
- Quota is now enforced
- Users can generate max 100 letters per month
- Resets automatically on 1st of month

## Common Quota Values

| Value | Use Case |
|-------|----------|
| 50 | Small team testing |
| 100 | Normal user limit |
| 500 | Premium users |
| 1000 | Power users |
| Not set | Unlimited |

## Error When Quota Exceeded

```json
HTTP 429
{
  "error": "تم تجاوز حد الخطابات الشهري",
  "quota_info": {
    "current_count": 100,
    "quota_limit": 100
  }
}
```

## Check Current Usage

```python
from src.services.usage_tracking_service import get_usage_tracking_service

service = get_usage_tracking_service()
result = service.check_quota(sheet_id)

# result = {
#   "status": "allowed" | "exceeded",
#   "current_count": 25,
#   "quota_limit": 100,
#   "remaining": 75
# }
```

## Remove/Modify Quota

**Remove quota**: Delete the quota_month row from Settings sheet → Unlimited generation

**Change limit**: Update the value in Settings sheet → New limit takes effect immediately

**Example**: Change from 100 → 500
```
Before:
key           | value
quota_month   | 100

After:
key           | value
quota_month   | 500
```

## Testing

### Test 1: Check it works
1. Set quota_month = 3
2. Generate 3 letters ✓ (should work)
3. Generate 4th letter ✗ (should fail with 429)

### Test 2: Check it resets
1. Wait until 1st of next month
2. Generate letter ✓ (should work - counter reset)

### Test 3: Remove quota
1. Delete quota_month row
2. Generate letter ✓ (should work - no limit)

## Files Modified

| File | Changes |
|------|---------|
| `src/services/usage_tracking_service.py` | Added quota methods |
| `src/api/letter_routes.py` | Added quota check |
| `docs/USAGE_TRACKING_DOCUMENTATION.md` | Updated documentation |

## Key Points

⭐ Quota is checked BEFORE letter generation  
⭐ Monthly reset happens automatically  
⭐ Each user's Settings sheet applies to their quota  
⭐ No Settings sheet = unlimited generation  
⭐ Errors don't block generation (fail open)  

## Columns Required

### Settings Sheet
```
Column 1: key
Column 2: value
```

Must have headers in row 1, data starts at row 2.

## API Response with Quota Info

**When exceeded (429)**:
```json
{
  "error": "تم تجاوز حد الخطابات الشهري",
  "message": "Monthly letter quota has been reached",
  "quota_info": {
    "current_count": 100,
    "quota_limit": 100
  }
}
```

**When allowed (200 - normal letter response)**:
```json
{
  "ID": "...",
  "Title": "...",
  "Letter": "...",
  "usage": {
    "total_tokens": 4270,
    "cost_usd": 0.1065
  }
}
```

## Troubleshooting Quick Tips

| Issue | Solution |
|-------|----------|
| Quota not working | Restart app, check Settings sheet exists |
| Wrong limit | Verify quota_month value is a number |
| Can't generate anymore | Check if quota_month limit reached |
| Want unlimited | Remove quota_month row from Settings |

---

For detailed information, see [QUOTA_ENFORCEMENT_README.md](./QUOTA_ENFORCEMENT_README.md)
