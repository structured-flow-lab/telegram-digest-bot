import { greeting } from './greeting';

export default function App() {
  return (
    <main style={{ fontFamily: 'system-ui', padding: '2rem' }}>
      <h1>{greeting('telegram-digest-bot')}</h1>
      <p>Reads selected public Telegram channels and generates a short AI digest for a requested period.</p>
    </main>
  );
}
