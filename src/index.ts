import 'dotenv/config';
import { bootstrap } from './app.js';
import { getLogger } from './services/logger.js';

async function main(): Promise<void> {
  try {
    await bootstrap();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`Fatal error: ${message}`);
    process.exit(1);
  }
}

process.on('unhandledRejection', (reason) => {
  try {
    getLogger().fatal({ reason }, 'Unhandled rejection');
  } catch {
    console.error('Unhandled rejection:', reason);
  }
  process.exit(1);
});

void main();
