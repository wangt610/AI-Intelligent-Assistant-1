import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { ChatArea } from '../chat/ChatArea';
import { InputArea } from '../chat/InputArea';
import { ToastContainer } from '../ui/Toast';

export function Layout() {
  return (
    <div className="flex h-screen bg-bg text-text overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <ChatArea />
        <InputArea />
      </div>
      <ToastContainer />
    </div>
  );
}
