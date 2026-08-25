import {
  sql,
} from "@/lib/db";

export type SavedChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: string[];
  createdAt: string;
};

export type SavedConversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
};

type ConversationRow = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type MessageRow = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: unknown;
  created_at: string;
};

function parseSources(
  value: unknown
): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (source): source is string =>
      typeof source === "string"
  );
}

function requireUserId(
  userId: string
) {
  if (!userId) {
    throw new Error(
      "User ID is required."
    );
  }
}

/* ========================================
   CREATE USER CONVERSATION
======================================== */

export async function createConversation(
  userId: string,
  firstMessage: string
): Promise<SavedConversation> {
  requireUserId(userId);

  const cleanMessage =
    firstMessage.trim();

  const title =
    cleanMessage.length > 55
      ? `${cleanMessage.slice(
          0,
          55
        )}...`
      : cleanMessage ||
        "New conversation";

  const rows = await sql`
    INSERT INTO conversations (
      user_id,
      title
    )
    VALUES (
      ${userId},
      ${title}
    )
    RETURNING
      id,
      title,
      created_at,
      updated_at
  `;

  const row =
    rows[0] as
      | ConversationRow
      | undefined;

  if (!row) {
    throw new Error(
      "The conversation could not be created."
    );
  }

  return {
    id: String(row.id),
    title: row.title,
    createdAt:
      row.created_at,
    updatedAt:
      row.updated_at,
  };
}

/* ========================================
   SAVE USER MESSAGE
======================================== */

export async function saveChatMessage(
  conversationId: string,
  userId: string,
  role: "user" | "assistant",
  content: string,
  sources: string[] = []
): Promise<void> {
  requireUserId(userId);

  /*
   * INSERT ... SELECT ensures that a message
   * is inserted only when the conversation
   * belongs to the signed-in user.
   */
  const insertedRows = await sql`
    INSERT INTO conversation_messages (
      conversation_id,
      role,
      content,
      sources
    )
    SELECT
      c.id,
      ${role},
      ${content},
      ${JSON.stringify(
        sources
      )}::jsonb
    FROM conversations c
    WHERE c.id = ${conversationId}
      AND c.user_id = ${userId}
    RETURNING id
  `;

  if (insertedRows.length === 0) {
    throw new Error(
      "Conversation not found or access denied."
    );
  }

  await sql`
    UPDATE conversations
    SET updated_at = NOW()
    WHERE id = ${conversationId}
      AND user_id = ${userId}
  `;
}

/* ========================================
   GET USER CONVERSATIONS
======================================== */

export async function getConversations(
  userId: string
): Promise<SavedConversation[]> {
  requireUserId(userId);

  const rows = await sql`
    SELECT
      id,
      title,
      created_at,
      updated_at
    FROM conversations
    WHERE user_id = ${userId}
    ORDER BY updated_at DESC
    LIMIT 50
  `;

  return (
    rows as ConversationRow[]
  ).map((row) => ({
    id: String(row.id),
    title: row.title,
    createdAt:
      row.created_at,
    updatedAt:
      row.updated_at,
  }));
}

/* ========================================
   GET USER CONVERSATION MESSAGES
======================================== */

export async function getConversationMessages(
  conversationId: string,
  userId: string
): Promise<SavedChatMessage[]> {
  requireUserId(userId);

  /*
   * Joining conversations ensures that
   * messages are returned only when the
   * conversation belongs to this user.
   */
  const rows = await sql`
    SELECT
      cm.id,
      cm.role,
      cm.content,
      cm.sources,
      cm.created_at
    FROM conversation_messages cm
    INNER JOIN conversations c
      ON c.id = cm.conversation_id
    WHERE
      cm.conversation_id =
        ${conversationId}
      AND c.user_id =
        ${userId}
    ORDER BY cm.created_at ASC
  `;

  return (
    rows as MessageRow[]
  ).map((row) => ({
    id: String(row.id),
    role: row.role,
    content: row.content,
    sources:
      parseSources(
        row.sources
      ),
    createdAt:
      row.created_at,
  }));
}

/* ========================================
   DELETE USER CONVERSATION
======================================== */

export async function deleteConversation(
  conversationId: string,
  userId: string
): Promise<boolean> {
  requireUserId(userId);

  const rows = await sql`
    DELETE FROM conversations
    WHERE id = ${conversationId}
      AND user_id = ${userId}
    RETURNING id
  `;

  return rows.length > 0;
}