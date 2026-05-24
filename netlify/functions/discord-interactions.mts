/**
 * Discord Interactions Endpoint
 *
 * Receives signed HTTP POST requests from Discord whenever a slash command
 * or other interaction fires. Discord requires this endpoint to:
 *   1. Respond to PING challenges with PONG (used to verify the URL)
 *   2. Verify every request's Ed25519 signature using DISCORD_PUBLIC_KEY
 *   3. Reply to APPLICATION_COMMAND interactions within 3 seconds
 *
 * Environment variables (set in Netlify → Site configuration → Environment variables):
 *   DISCORD_PUBLIC_KEY  — Application Public Key from Discord Developer Portal
 *   DISCORD_TOKEN       — Bot token, used for follow-up REST API calls
 */

import type { Config } from '@netlify/functions'

// ─── Discord type constants ───────────────────────────────────────────────────

const InteractionType = {
  PING: 1,
  APPLICATION_COMMAND: 2,
  MESSAGE_COMPONENT: 3,
  APPLICATION_COMMAND_AUTOCOMPLETE: 4,
  MODAL_SUBMIT: 5,
} as const

const ResponseType = {
  PONG: 1,
  CHANNEL_MESSAGE_WITH_SOURCE: 4,
  DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE: 5,
} as const

const MessageFlags = {
  EPHEMERAL: 64,
} as const

// ─── Types ────────────────────────────────────────────────────────────────────

interface CommandOption {
  name: string
  type: number
  value?: string | number | boolean
}

interface InteractionData {
  id: string
  name: string
  type: number
  options?: CommandOption[]
}

interface DiscordUser {
  id: string
  username: string
  discriminator: string
}

interface DiscordMember {
  user: DiscordUser
  permissions: string
  roles: string[]
}

interface DiscordInteraction {
  id: string
  type: number
  data?: InteractionData
  guild_id?: string
  channel_id?: string
  member?: DiscordMember
  user?: DiscordUser
  token: string
  version: number
}

// ─── Signature verification ───────────────────────────────────────────────────

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

async function verifyDiscordSignature(
  rawBody: string,
  signature: string,
  timestamp: string,
  publicKey: string,
): Promise<boolean> {
  try {
    const key = await crypto.subtle.importKey(
      'raw',
      hexToBytes(publicKey),
      { name: 'Ed25519' },
      false,
      ['verify'],
    )
    const message = new TextEncoder().encode(timestamp + rawBody)
    return crypto.subtle.verify('Ed25519', key, hexToBytes(signature), message)
  } catch {
    return false
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * Make a Discord REST API call using the bot token.
 * Used for follow-up messages after a deferred response.
 */
async function discordApiCall(
  path: string,
  method: string,
  body?: unknown,
): Promise<void> {
  const token = Netlify.env.get('DISCORD_TOKEN')
  if (!token) {
    console.error('[discord-interactions] DISCORD_TOKEN not set — cannot call Discord REST API')
    return
  }
  await fetch(`https://discord.com/api/v10${path}`, {
    method,
    headers: {
      Authorization: `Bot ${token}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  })
}

// ─── Command routing ──────────────────────────────────────────────────────────

/**
 * Add new slash command handlers here.
 * Each case should return a valid Discord interaction response object.
 */
async function handleApplicationCommand(
  interaction: DiscordInteraction,
): Promise<Response> {
  const name = (interaction.data?.name ?? '').toLowerCase()

  switch (name) {
    case 'ping':
      return jsonResponse({
        type: ResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: { content: 'Pong! Bot aktif ve yanıt veriyor.' },
      })

    case 'yardim':
    case 'help': {
      const embed = {
        title: 'Bot Komutları',
        description:
          'Bu Discord botu artık Netlify üzerinde çalışan bir interaction endpoint\'i olarak hizmet vermektedir.\n\n' +
          'Mevcut komutlar:\n' +
          '• `/ping` — Botun aktif olup olmadığını kontrol eder\n' +
          '• `/yardim` — Bu mesajı gösterir',
        color: 0x5865f2,
      }
      return jsonResponse({
        type: ResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: { embeds: [embed], flags: MessageFlags.EPHEMERAL },
      })
    }

    default:
      return jsonResponse({
        type: ResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        data: {
          content: `\`/${name}\` komutu bu endpoint üzerinde tanınmadı.`,
          flags: MessageFlags.EPHEMERAL,
        },
      })
  }
}

// ─── Main handler ─────────────────────────────────────────────────────────────

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 })
  }

  // Read and verify signature before parsing body
  const signature = req.headers.get('x-signature-ed25519')
  const timestamp = req.headers.get('x-signature-timestamp')
  const publicKey = Netlify.env.get('DISCORD_PUBLIC_KEY')

  if (!signature || !timestamp) {
    return new Response('Bad Request: missing signature headers', { status: 400 })
  }

  if (!publicKey) {
    console.error('[discord-interactions] DISCORD_PUBLIC_KEY environment variable is not set')
    return new Response('Internal Server Error', { status: 500 })
  }

  const rawBody = await req.text()

  const isValid = await verifyDiscordSignature(rawBody, signature, timestamp, publicKey)
  if (!isValid) {
    return new Response('Unauthorized: invalid request signature', { status: 401 })
  }

  let interaction: DiscordInteraction
  try {
    interaction = JSON.parse(rawBody)
  } catch {
    return new Response('Bad Request: invalid JSON', { status: 400 })
  }

  // Discord sends a PING when the URL is first registered — must reply PONG
  if (interaction.type === InteractionType.PING) {
    return jsonResponse({ type: ResponseType.PONG })
  }

  if (interaction.type === InteractionType.APPLICATION_COMMAND) {
    return handleApplicationCommand(interaction)
  }

  return new Response('Unhandled interaction type', { status: 400 })
}

export const config: Config = {
  // Discord will POST interactions to this path.
  // Register this URL in Discord Developer Portal →
  //   Applications → <your app> → General Information → Interactions Endpoint URL
  // Full URL: https://<your-netlify-site>.netlify.app/api/discord/interactions
  path: '/api/discord/interactions',
  method: 'POST',
}
