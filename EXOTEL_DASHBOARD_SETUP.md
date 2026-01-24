# 📞 Exotel Dashboard Setup Guide - WebSocket Test Mode

This guide walks you through configuring Exotel to connect to your Railway WebSocket endpoint.

---

## 🎯 Step-by-Step Configuration

### **Method 1: Using Voicebot App (Easiest)**

#### **Step 1: Login to Exotel**
- URL: https://my.exotel.com/goldmines2
- Login with your credentials

---

#### **Step 2: Navigate to Apps**
1. Click **"Apps"** in the left sidebar menu
2. You'll see options like:
   - Exophones
   - **Voicebot Apps** ← Click this
   - Exoflows
   - etc.

---

#### **Step 3: Create Voicebot App**
1. Click **"+ Create Voicebot App"** button (top right)
2. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **App Name** | `AI Voice Agent Test` |
   | **Description** | `WebSocket test for Railway deployment` |
   | **WebSocket URL** | `wss://ai-voice-agent-production-9d41.up.railway.app/media` |
   | **Audio Format** | `mulaw/8000` or `l16/8000` (check Exotel docs) |
   | **Protocol Version** | `1.0` or latest |

   ⚠️ **CRITICAL**: Use `wss://` (WebSocket Secure), NOT `https://`

3. Click **"Save"** or **"Create"**

---

#### **Step 4: Attach App to Your Virtual Number**
1. Go to **"Exophones"** in the left sidebar
2. Find your number: **01414939962**
3. Click **"Edit"** or the settings icon (⚙️)
4. Under **"Incoming Call Settings"** or **"Connect to"**:
   - Select: **"Voicebot App"**
   - Choose: **"AI Voice Agent Test"** (the app you just created)
5. Click **"Save"**

---

### **Method 2: Using Exoflows (Advanced)**

If you prefer using Exotel's flow builder:

1. Go to **"Exoflows"** → **"Create New Flow"**
2. Add a **"Connect to Voicebot"** widget
3. Configure the widget:
   - **WebSocket URL**: `wss://ai-voice-agent-production-9d41.up.railway.app/media`
4. Connect the flow to your virtual number `01414939962`

---

## ✅ Verification Checklist

Before making a test call, verify:

- [ ] Voicebot App created with correct WebSocket URL
- [ ] WebSocket URL uses `wss://` (not `https://`)
- [ ] App is attached to virtual number `01414939962`
- [ ] Railway deployment is running (check: https://ai-voice-agent-production-9d41.up.railway.app/)
- [ ] Test mode is enabled (response should show `"test_mode": true`)

---

## 📞 Making a Test Call

### **Option A: Inbound Call (Easiest)**

1. **Call your Exotel number from your phone**: `01414939962`
2. **Wait for connection** (~3-5 seconds)
3. **You should hear**: A 440Hz beep tone (1 second)
4. **Exotel will**:
   - Establish WebSocket connection to Railway
   - Send "connected" event
   - Send "start" event with call details
   - Start streaming audio (media events)
5. **Check Railway logs immediately!**

---

### **Option B: Outbound Call via API**

If you want to make an outbound call to test:

1. Edit the test script I created: `test_exotel_call.sh`
2. Replace `TO_NUMBER="+91XXXXXXXXXX"` with your actual phone number
3. Run the script:
   ```bash
   chmod +x test_exotel_call.sh
   ./test_exotel_call.sh
   ```
4. Your phone will ring
5. Answer the call
6. WebSocket connection will be established

**Note**: For outbound calls, you might need to configure the WebSocket URL in the Exotel flow/applet that handles outbound calls.

---

## 📊 What to Expect in Railway Logs

After answering the call, you should see these logs in Railway:

```
INFO: 🧪 WebSocket server initialized in TEST MODE (no AI services)
INFO: WebSocket connection established
INFO: ✅ TEST: WebSocket CONNECTED event received
INFO:    Data: { ... }
INFO: ✅ TEST: Media streaming STARTED
INFO:    Call SID: abc123xyz
INFO:    From: +91XXXXXXXXXX
INFO:    To: 01414939962
INFO:    Session created: abc123xyz
INFO: ✅ TEST: Sent test audio (440Hz tone, 1 second)
INFO:    Audio size: 16000 bytes
INFO: ✅ TEST: MEDIA event #1 received
INFO:    Audio chunk (base64): UklGRiQAAABXQVZFZm10...
INFO: ✅ TEST: MEDIA event #11 received
INFO: ✅ TEST: MEDIA event #21 received
...
INFO: ✅ TEST: Call STOPPED
INFO:    Total media chunks received: 156
INFO: WebSocket connection closed
```

---

## 🔍 Troubleshooting

### **No logs appear in Railway**
❌ **Problem**: Exotel is not connecting to your WebSocket

**Check**:
1. Is the WebSocket URL correct in Exotel dashboard?
   - Should be: `wss://ai-voice-agent-production-9d41.up.railway.app/media`
   - NOT: `https://...` or `ws://...` (non-secure)
2. Is the Voicebot App attached to the correct number?
3. Is Railway deployment healthy?
   - Check: https://ai-voice-agent-production-9d41.up.railway.app/
   - Should return JSON with `"status": "running"`

---

### **Logs show "connected" but no "start"**
❌ **Problem**: WebSocket connected but call didn't start streaming

**Check**:
1. Did you answer the call?
2. Is your phone's microphone working?
3. Check Exotel dashboard logs for errors

---

### **Connection refused / timeout**
❌ **Problem**: Railway service is down or WebSocket endpoint is not accessible

**Check**:
1. Railway service status
2. Railway logs for startup errors
3. Try accessing: https://ai-voice-agent-production-9d41.up.railway.app/health

---

### **Exotel shows "Invalid WebSocket URL"**
❌ **Problem**: URL format is incorrect

**Fix**:
- Use `wss://` (WebSocket Secure) for HTTPS domains
- Use `ws://` only for HTTP (not recommended)
- Ensure no trailing slashes or extra parameters

---

## 🎯 Next Steps After Successful Test

Once you see logs showing:
- ✅ `connected` event
- ✅ `start` event with call details
- ✅ `media` events (incoming audio)
- ✅ Test audio sent successfully
- ✅ `stop` event

**You're ready for Phase 2**: Enable AI services one by one!

---

## 📞 Need Help?

Common Exotel support resources:
- Dashboard: https://my.exotel.com/goldmines2
- Docs: https://developer.exotel.com/
- API Reference: https://developer.exotel.com/api/
- Support: support@exotel.com

---

## 🔑 Quick Reference

**Your Configuration**:
```
Exotel Account SID: goldmines2
Virtual Number: 01414939962
WebSocket URL: wss://ai-voice-agent-production-9d41.up.railway.app/media
Railway URL: https://ai-voice-agent-production-9d41.up.railway.app
Test Mode: Enabled (EXOTEL_TEST_MODE=true)
```

**What works in test mode**:
- ✅ WebSocket connection
- ✅ Event logging (connected, start, media, stop)
- ✅ Test audio playback (440Hz tone)
- ❌ Speech-to-Text (Deepgram) - disabled
- ❌ AI conversation (OpenAI) - disabled
- ❌ Text-to-Speech (ElevenLabs) - disabled

**To enable production mode**:
Set `EXOTEL_TEST_MODE=false` in Railway environment variables.
