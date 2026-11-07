import { useEffect } from 'react';
import { useActiveSession, useAppStore } from './lib/store';
import type { ArtifactState } from './lib/types';
import { getCanvasFeature } from './modules/registry';
import { TopBar } from './shell/TopBar';
import { LeftNav } from './shell/LeftNav';
import { ChatPanel } from './shell/ChatPanel';
import { CanvasPanel } from './shell/CanvasPanel';
import { StatusBar } from './shell/StatusBar';
import { LoginGate } from './shell/LoginGate';
import { Icon } from './shell/Icons';

/** 整页模块在还没有 artifact 时用它启动（receivedAt 固定，避免每次渲染重置页面状态）。 */
const EMPTY_ARTIFACT: ArtifactState = {
  artifactType: 'graph',
  data: {},
  receivedAt: 0,
};

export default function App() {
  const bootstrap = useAppStore((s) => s.bootstrap);
  const bootstrapped = useAppStore((s) => s.bootstrapped);
  const account = useAppStore((s) => s.account);
  const activeFeature = useAppStore((s) => s.activeFeature);
  const setDraft = useAppStore((s) => s.setDraft);
  const send = useAppStore((s) => s.send);
  const session = useActiveSession();

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  if (!bootstrapped) {
    return (
      <div className="boot-screen">
        <div className="boot-mark">
          <Icon name="pencil" size={26} />
        </div>
        <div className="boot-text">机械制图 AI 助教</div>
        <div className="boot-sub">
          <span className="spinner" /> 正在连接 /api/health 与 /api/modules…
        </div>
      </div>
    );
  }

  if (!account) return <LoginGate />;

  // 整页模式：当前模块的 feature 声明了 page → 主区整体让给它（左栏保留作为退出出口）。
  // 其它模块仍走标准三栏（ChatPanel + CanvasPanel），画布模式不受影响。
  const PageComponent = getCanvasFeature(activeFeature)?.page;
  const latestArtifact = session.artifacts[session.artifacts.length - 1] ?? EMPTY_ARTIFACT;

  return (
    <div className="app-shell">
      <TopBar />
      <div className="workbench">
        <LeftNav />
        {PageComponent ? (
          <div
            style={{
              gridColumn: '2 / -1',
              minWidth: 0,
              minHeight: 0,
              display: 'flex',
              overflow: 'hidden',
            }}
          >
            <PageComponent
              artifact={latestArtifact}
              onAsk={setDraft}
              messages={session.messages}
              busy={session.streaming}
              onSendMessage={(text) => {
                void send(text);
              }}
            />
          </div>
        ) : (
          <>
            <ChatPanel />
            <CanvasPanel />
          </>
        )}
      </div>
      <StatusBar />
    </div>
  );
}
