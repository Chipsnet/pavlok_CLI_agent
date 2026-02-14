/**
 * Oni System v0.3 - Cloudflare Worker Gateway
 *
 * ADR-001: Gateway責務境界に準拠
 *
 * 責務:
 * - Slack署名検証
 * - ユーザー→バックエンドのルーティング
 * - Replay攻撃対策
 * - レート制限
 *
 * デプロイ前に環境変数を設定:
 * - SLACK_SIGNING_SECRET
 * - USER_MAP (JSON文字列)
 * - KV_NAMESPACE (レート制限用)
 */

// ========================================
// 設定
// ========================================

const MAX_TIMESTAMP_AGE = 300; // 5分（replay攻撃対策）
const RATE_LIMIT_WINDOW = 60;  // 60秒ウィンドウ
const RATE_LIMIT_MAX = 20;     // 1分間に最大20リクエスト

// ========================================
// Slack署名検証
// ========================================

async function verifySlackSignature(request, body, signingSecret) {
  const timestamp = request.headers.get("X-Slack-Request-Timestamp");
  const signature = request.headers.get("X-Slack-Signature");

  if (!timestamp || !signature) {
    return { valid: false, error: "Missing signature headers" };
  }

  // Replay攻撃対策: タイムスタンプチェック
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - parseInt(timestamp)) > MAX_TIMESTAMP_AGE) {
    return { valid: false, error: "Timestamp too old" };
  }

  // Slack公式フォーマット: v0:timestamp:body
  const basestring = `v0:${timestamp}:${body}`;

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(signingSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(basestring));
  const hex = Array.from(new Uint8Array(sig))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");

  const expected = `v0=${hex}`;

  if (expected !== signature) {
    return { valid: false, error: "Invalid signature" };
  }

  return { valid: true, timestamp, signature };
}

// ========================================
// レート制限
// ========================================

async function checkRateLimit(userId, env) {
  if (!env.KV) {
    // KV が設定されていない場合はスキップ
    return { allowed: true };
  }

  const key = `rate:${userId}`;
  const count = await env.KV.get(key);
  const currentCount = parseInt(count || "0");

  if (currentCount >= RATE_LIMIT_MAX) {
    return { allowed: false, retryAfter: RATE_LIMIT_WINDOW };
  }

  await env.KV.put(key, (currentCount + 1).toString(), {
    expirationTtl: RATE_LIMIT_WINDOW
  });

  return { allowed: true };
}

// ========================================
// ペイロード解析
// ========================================

function parsePayload(body) {
  const params = new URLSearchParams(body);

  // Interactive payload (JSON)
  const payloadParam = params.get("payload");
  if (payloadParam) {
    try {
      return {
        type: "interactive",
        data: JSON.parse(payloadParam),
        raw: body
      };
    } catch (e) {
      return { type: "invalid", error: "Invalid JSON payload" };
    }
  }

  // Command payload (form data)
  const formData = Object.fromEntries(params);
  return {
    type: "command",
    data: formData,
    raw: body
  };
}

function extractUserId(payload) {
  if (payload.type === "interactive") {
    return payload.data?.user?.id;
  }
  return payload.data?.user_id;
}

// ========================================
// メインハンドラ
// ========================================

export default {
  async fetch(request, env, ctx) {
    // 設定取得
    const signingSecret = env.SLACK_SIGNING_SECRET;
    if (!signingSecret) {
      return new Response("Server misconfiguration", { status: 500 });
    }

    // USER_MAP取得（環境変数からJSON パース）
    let userMap = {};
    try {
      userMap = JSON.parse(env.USER_MAP || "{}");
    } catch (e) {
      return new Response("Invalid USER_MAP config", { status: 500 });
    }

    // リクエストボディ取得
    const body = await request.text();

    // 署名検証
    const sigResult = await verifySlackSignature(request, body, signingSecret);
    if (!sigResult.valid) {
      return new Response(sigResult.error, { status: 401 });
    }

    // ペイロード解析
    const payload = parsePayload(body);
    if (payload.type === "invalid") {
      return new Response(payload.error, { status: 400 });
    }

    // ユーザーID抽出
    const userId = extractUserId(payload);
    if (!userId) {
      return new Response("Cannot identify user", { status: 400 });
    }

    // ユーザールーティング
    const backendUrl = userMap[userId];
    if (!backendUrl) {
      return new Response("No backend for user", { status: 403 });
    }

    // レート制限チェック
    const rateResult = await checkRateLimit(userId, env);
    if (!rateResult.allowed) {
      return new Response("Rate limit exceeded", {
        status: 429,
        headers: { "Retry-After": String(rateResult.retryAfter) }
      });
    }

    // バックエンドへ転送（同期）
    // 元のリクエスト形式（フォームデータ）を維持
    // ヘッダーを転送してBackend側でも二重検証可能に
    const backendResponse = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": sigResult.timestamp,
        "X-Slack-Signature": sigResult.signature,
        "X-Forwarded-By": "cloudflare-gateway",
        "X-User-Id": userId
      },
      body: body
    });

    // Backendのレスポンスをそのまま返す
    return backendResponse;
  }
};
