import { Layout } from './components/layout/Layout';
import { SettingsModal } from './components/modals/SettingsModal';
import { ShortcutCheatsheet } from './components/modals/ShortcutCheatsheet';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

export default function App() {
  useKeyboardShortcuts();

  return (
    <>
      <Layout />
      <SettingsModal />
      <ShortcutCheatsheet />
    </>
  );
}
