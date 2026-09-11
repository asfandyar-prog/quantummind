/**
 * The recent turns sent with each message so the tutor can follow the
 * conversation (the backend replays at most the last 12). Seeded welcome
 * messages are UI decoration, not something the student said, so they are
 * left out.
 */
export function recentHistory(messages, limit = 12) {
  return messages
    .filter(m => !m.demo && m.content)
    .slice(-limit)
    .map(({ role, content }) => ({ role, content }))
}
