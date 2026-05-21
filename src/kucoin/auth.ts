import crypto from 'node:crypto';

export type AuthCredentials = {
  apiKey: string;
  apiSecret: string;
  passphrase: string;
};

export function signRequest(
  credentials: AuthCredentials,
  method: string,
  endpoint: string,
  body: string,
  timestamp: number,
): { signature: string; passphrase: string } {
  const strToSign = `${timestamp}${method.toUpperCase()}${endpoint}${body}`;
  const signature = crypto
    .createHmac('sha256', credentials.apiSecret)
    .update(strToSign)
    .digest('base64');

  const passphrase = crypto
    .createHmac('sha256', credentials.apiSecret)
    .update(credentials.passphrase)
    .digest('base64');

  return { signature, passphrase };
}

export function generateClientOid(prefix = 'whale-bot'): string {
  return `${prefix}-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
}
