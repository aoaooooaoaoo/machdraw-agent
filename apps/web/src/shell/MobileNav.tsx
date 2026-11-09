import { useAppStore } from '../lib/store';
import { Icon } from './Icons';

/** 窄屏底部导航：模块 / 对话 / 画布 / 图谱（桌面端隐藏）。 */
export function MobileNav() {
  const setMobileNavOpen = useAppStore((s) => s.setMobileNavOpen);
  const setActiveFeature = useAppStore((s) => s.setActiveFeature);
  const mobileNavOpen = useAppStore((s) => s.mobileNavOpen);

  function scrollTo(selector: string) {
    document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <nav className="mobile-nav" aria-label="移动端导航">
      <button
        type="button"
        className={mobileNavOpen ? 'is-active' : ''}
        onClick={() => setMobileNavOpen(!mobileNavOpen)}
      >
        <Icon name="layers" size={18} />
        <span>模块</span>
      </button>
      <button type="button" onClick={() => scrollTo('.chat')}>
        <Icon name="chat" size={18} />
        <span>对话</span>
      </button>
      <button type="button" onClick={() => scrollTo('.canvas')}>
        <Icon name="pencil" size={18} />
        <span>画布</span>
      </button>
      <button
        type="button"
        onClick={() => {
          setActiveFeature('graph');
          setMobileNavOpen(false);
        }}
      >
        <Icon name="graph" size={18} />
        <span>图谱</span>
      </button>
    </nav>
  );
}
