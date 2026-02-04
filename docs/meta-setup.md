# Meta API Setup Guide

Step-by-step guide to get your Meta (Facebook) Marketing API credentials for Funnel Optimizer.

## Prerequisites

- A Facebook account with admin access to a Facebook Page
- A Meta Business Suite account (business.facebook.com)
- An active Ad Account connected to the business

## Step 1: Create a Meta Developer App

1. Go to https://developers.facebook.com/apps/
2. Click "Create App"
3. Choose "Other" use case, then "Business" type
4. Name it (e.g. "Funnel Optimizer") and link to your Business
5. Once created, go to App Settings > Basic
6. Copy **App ID** → `FO_META_APP_ID`
7. Copy **App Secret** → `FO_META_APP_SECRET`

## Step 2: Add Marketing API Product

1. In your app dashboard, click "Add Product"
2. Find "Marketing API" and click "Set Up"
3. This enables the ads_management and ads_read permissions

## Step 3: Generate Access Token

### Option A: Short-lived token (for testing)

1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app from the dropdown
3. Click "Generate Access Token"
4. Grant these permissions when prompted:
   - `ads_management`
   - `leads_retrieval`
   - `pages_manage_ads`
   - `pages_read_engagement`
5. Copy the token → `FO_META_ACCESS_TOKEN`

**Note:** This token expires in ~1 hour. For production, use a long-lived token.

### Option B: Long-lived token (for production)

1. Get a short-lived token (Option A above)
2. Exchange it for a long-lived token:

```bash
curl "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_TOKEN"
```

3. The response contains an `access_token` that lasts ~60 days
4. Copy it → `FO_META_ACCESS_TOKEN`

### Option C: System User token (recommended for production)

1. Go to Business Settings > System Users
2. Create a new System User with "Admin" role
3. Assign it to your Ad Account with "Manage campaigns" permission
4. Generate a token for it — this token doesn't expire
5. Copy it → `FO_META_ACCESS_TOKEN`

## Step 4: Find Your Ad Account ID

1. Go to https://business.facebook.com/settings/ad-accounts
2. Click on your ad account
3. The Account ID is shown (e.g. `123456789`)
4. Add the `act_` prefix → `FO_META_AD_ACCOUNT_ID=act_123456789`

## Step 5: Find Your Facebook Page ID

1. Go to your Facebook Page
2. Click "About" or look in the URL
3. Or use the API: go to Graph API Explorer, query `me/accounts`, find your page's `id`
4. Copy it → `FO_META_PAGE_ID`

## Step 6: Privacy Policy URL

Lead gen forms require a privacy policy link.

- If you have one: use it → `FO_PRIVACY_POLICY_URL`
- If not: create a simple one on your website, or use a service like Termly/PrivacyPolicies.com

## Step 7: Configure .env

```bash
cp .env.example .env
```

Fill in all values:

```
FO_META_APP_ID=your_app_id
FO_META_APP_SECRET=your_app_secret
FO_META_ACCESS_TOKEN=your_access_token
FO_META_AD_ACCOUNT_ID=act_your_account_id
FO_META_PAGE_ID=your_page_id
FO_META_API_VERSION=v21.0
FO_PRIVACY_POLICY_URL=https://yoursite.com/privacy
FO_DB_PATH=data/pipeline.db
```

## Step 8: Verify

```bash
funnel db check-meta
```

Expected output:
```
Meta API connection OK
  name: Your Ad Account Name
  account_id: 123456789
  account_status: 1
  currency: USD
  timezone_name: America/Chicago
```

If it fails, double-check:
- Token has the right permissions
- Ad account ID has `act_` prefix
- App is in "Live" mode (not "Development") for production use

## Required Permissions Summary

| Permission | Used for |
|-----------|----------|
| `ads_management` | Create/update campaigns, ad sets, ads |
| `leads_retrieval` | Read lead form submissions |
| `pages_manage_ads` | Create lead gen forms on your Page |
| `pages_read_engagement` | Read Page data for ad creation |

## Common Issues

**"Application does not have permission for this action"**
- Make sure the app has Marketing API product added
- Make sure the token has all 4 permissions listed above

**"Invalid OAuth access token"**
- Token may have expired — regenerate it
- For production, use a System User token

**"Ad account not found"**
- Check the `act_` prefix on the account ID
- Make sure the token's user has access to the ad account

**"Reach estimate too low"**
- Your targeting is too narrow — expand geo or age range
- This usually shows up when creating ad sets
