/**
 * symphony/handler.js - OpenClaw Skill 前端
 *
 * 接收 OpenClaw 消息，RPC 到 Python 后端
 */
const http = require('http');

const SYMPHONY_HOST = '127.0.0.1';
const SYMPHONY_PORT = 18081;

// ── RPC 工具 ────────────────────────────────────────────────────────
function rpc(endpoint, body) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify(body);
        const options = {
            hostname: SYMPHONY_HOST,
            port: SYMPHONY_PORT,
            path: endpoint,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
            timeout: 30000,
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch {
                    resolve({ error: 'Invalid JSON', raw: data.slice(0, 200) });
                }
            });
        });

        req.on('error', err => reject(err));
        req.on('timeout', () => { req.destroy(); reject(new Error('RPC timeout')); });
        req.write(postData);
        req.end();
    });
}

// ── 主入口 ─────────────────────────────────────────────────────────
/**
 * params: {
 *   data: {
 *     message: string,      // 用户消息
 *     state?: string,       // 当前状态
 *     session_id?: string,  // 会话ID
 *   },
 *   ctx: null
 * }
 */
module.exports = async function handler(params) {
    const { message, session_id = 'default' } = params.data || {};

    if (!message) {
        return { error: 'message is required' };
    }

    // 检查后端是否可用
    try {
        const health = await rpc('/health', {});
        if (health.status !== 'ok') {
            return { error: 'symphony backend unavailable' };
        }
    } catch {
        return {
            error: 'symphony 后端未启动',
            hint: '请运行: python3 -m server.symphony_server',
        };
    }

    // 调用 thinking dialog
    const result = await rpc('/thinking/dialog', {
        message,
        session_id,
    });

    // 格式化返回
    const state = result.state || 'unknown';
    const response = result.response || '';

    // 根据状态返回不同格式
    if (state === 'clarifying' && result.questions?.length) {
        // 澄清问题 - 直接展示给用户
        return {
            text: response || result.questions[0],
            state,
        };
    }

    if (state === 'planning') {
        return {
            text: `📋 **执行计划**\n\n${result.plan || '(无计划)'}`,
            state,
            skill_requests: result.skill_requests || [],
        };
    }

    if (state === 'executing') {
        return {
            text: `⏳ ${response || '正在执行...'}`,
            state,
            skill_requests: result.skill_requests || [],
        };
    }

    if (state === 'completed') {
        return {
            text: response || '✅ 任务完成',
            state,
        };
    }

    return {
        text: response || '正在思考...',
        state,
    };
}
