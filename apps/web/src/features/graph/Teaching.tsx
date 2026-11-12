import { useEffect, useState } from 'react';
import { getTeachingCourse, reviewCase, type TeachingCourse, type TeachingReview } from '../../lib/api';
import type { GraphFull } from '../../lib/types';
import './teaching.css';

type Case = TeachingCourse['cases'][number];
type Attempt = {
  scores: Record<string, number>;
  source: 'self' | 'ai';
  initial?: string;
  answer?: string;
  choice?: string;
  quotes?: Record<string, string>;
  at?: number;
};
type Practice = Record<string, Attempt[]>;

export function useTeachingCourse() {
  const [course, setCourse] = useState<TeachingCourse | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    getTeachingCourse().then(
      (data) => { if (active) setCourse(data); },
      (err: Error) => { if (active) setError(err.message); },
    );
    return () => { active = false; };
  }, []);
  return { course, error };
}

function loadPractice(key: string): Practice {
  try {
    const data = JSON.parse(localStorage.getItem(key) ?? '{}') as Record<string, Attempt | Attempt[]> | null;
    return Object.fromEntries(Object.entries(data ?? {}).map(([id, record]) => [
      id, Array.isArray(record) ? record : record?.scores ? [record] : [],
    ]));
  } catch {
    return {};
  }
}

interface Props {
  course: TeachingCourse;
  full: GraphFull | null;
  account: string;
  mode: 'ability' | 'cases';
  caseId: string | null;
  abilityId: string | null;
  onCase: (id: string) => void;
  onQuestion: (id: string) => void;
  onKnowledge: (id: string) => void;
  onAbility: (id: string) => void;
}

export function Teaching({ course, full, account, mode, caseId, abilityId, onCase, onQuestion, onKnowledge, onAbility }: Props) {
  const storageKey = `rp.case-practice.v1.${account}`;
  const [practice, setPractice] = useState(() => loadPractice(storageKey));
  const [theme, setTheme] = useState('');
  const [caseQuery, setCaseQuery] = useState('');
  const ability = course.abilities.find((item) => item.id === abilityId) ?? course.abilities[0];
  const themes = [...new Set(course.cases.flatMap((item) => item.theme ? [item.theme] : []))];
  const visibleCases = course.cases.filter((item) => (!theme || item.theme === theme) &&
    (!caseQuery.trim() || `${item.title} ${item.context} ${item.question_ids.join(' ')}`
      .toLowerCase().includes(caseQuery.trim().toLowerCase())));
  const selectedCase = visibleCases.find((item) => item.id === caseId) ?? visibleCases[0];
  const byAbility = new Map(course.abilities.map((item) => [item.id, item]));
  const successors = course.abilities.filter((item) => item.prerequisites.includes(ability.id));
  const openCase = (id: string) => {
    setTheme('');
    setCaseQuery('');
    onCase(id);
  };
  const depth = (id: string): number => {
    const parents = byAbility.get(id)?.prerequisites ?? [];
    return parents.length ? 1 + Math.max(...parents.map(depth)) : 0;
  };
  const evidence = course.cases.flatMap((item) => item.rubric
    .filter((row) => row.ability_id === ability.id)
    .map((row) => ({ item, row, attempts: practice[item.id] ?? [] })));

  return (
    <div className="teaching-view">
      {mode === 'ability' ? (
        <>
          <h2>能力图谱</h2>
          <p className="teaching-muted">选择能力，查看前置能力、考查案例、评分项及历次作答证据。</p>
          <div className="teaching-map" aria-label="课程能力递进">
            {['基础能力', '应用与分析', '综合评价'].map((name, index) => (
              <div className="teaching-stage" key={name}>
                <h3>{name}</h3>
                {course.abilities.filter((item) => depth(item.id) === index).map((item) => (
                  <button key={item.id} aria-pressed={ability.id === item.id} onClick={() => onAbility(item.id)}>
                    <strong>{item.title}</strong>
                    <span>{item.outcome}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
          <section className="teaching-card">
            <h3>{ability.title}</h3>
            {ability.prerequisites.length > 0 && <div className="teaching-links">
              <span>前置能力</span>
              {ability.prerequisites.map((id) => (
                <button key={id} onClick={() => onAbility(id)}>{byAbility.get(id)?.title}</button>
              ))}
            </div>}
            {successors.length > 0 && <div className="teaching-links">
              <span>后续能力</span>
              {successors.map((item) => <button key={item.id} onClick={() => onAbility(item.id)}>{item.title}</button>)}
            </div>}
            <h4>考查任务与作答证据</h4>
            <ul className="teaching-evidence">
              {evidence.map(({ item, row, attempts }) => (
                <li key={row.id}>
                  <button onClick={() => openCase(item.id)}>{item.title}</button>
                  <span>{row.title}</span>
                  {item.question_ids.slice(-1).map((qid) => (
                    <button key={qid} onClick={() => onQuestion(qid)}>综合问题 {qid}</button>
                  ))}
                  <strong>{attempts[0]?.scores[row.id] == null ? '待练习'
                    : `${attempts[0].scores[row.id]} / ${row.points} · ${attempts[0].source === 'ai' ? '模型建议' : '自评'}`}</strong>
                  {attempts.length > 0 && <details className="teaching-attempts">
                    <summary>查看作答证据（{attempts.length} 次）</summary>
                    {attempts.map((attempt, index) => (
                      <div key={index} className="teaching-criterion">
                        <strong>{attempt.at ? new Date(attempt.at).toLocaleString('zh-CN') : '早期记录'}</strong>
                        <p>{attempt.scores[row.id]} / {row.points} 分 · {attempt.source === 'ai' ? '模型建议' : '自评'}</p>
                        {attempt.choice && <p>所选证据 · {item.scenario?.choices.find((choice) => choice.id === attempt.choice)?.label}</p>}
                        {attempt.initial && <blockquote><b>初判</b> {attempt.initial}</blockquote>}
                        {attempt.answer && <blockquote><b>修订作答</b> {attempt.answer}</blockquote>}
                        {attempt.quotes?.[row.id] && <blockquote><b>本评分项引文</b> {attempt.quotes[row.id]}</blockquote>}
                      </div>
                    ))}
                  </details>}
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : (
        <>
          <h2>工程案例 <span className="teaching-count">{course.cases.length} 个</span></h2>
          <div className="teaching-catalog-filters">
            <label>按主题筛选 <select value={theme} onChange={(event) => setTheme(event.target.value)}>
              <option value="">全部主题</option>
              {themes.map((name) => <option key={name}>{name}</option>)}
            </select></label>
            <label>搜索案例 <input value={caseQuery} onChange={(event) => setCaseQuery(event.target.value)}
              placeholder="案例、关键词或问题编号" /></label>
          </div>
          <nav className="teaching-catalog" aria-label="案例列表">
            {visibleCases.map((item) => (
              <button key={item.id} aria-pressed={selectedCase?.id === item.id} onClick={() => onCase(item.id)}>
                <strong>{item.title}</strong>
                <span>{item.theme} · {new Set(item.rubric.map((row) => row.ability_id)).size} 项能力</span>
              </button>
            ))}
          </nav>
          {selectedCase ? <CaseExercise
            key={selectedCase.id}
            item={selectedCase}
            full={full}
            onQuestion={onQuestion}
            onKnowledge={onKnowledge}
            onAbility={onAbility}
            onSave={(attempt) => {
              const saved = loadPractice(storageKey);
              const previous = saved[selectedCase.id] ?? [];
              const others = previous.filter((entry) => entry.answer !== attempt.answer || entry.choice !== attempt.choice
                || entry.initial !== attempt.initial || entry.source !== attempt.source);
              const next = { ...saved, [selectedCase.id]: [attempt, ...others].slice(0, 5) };
              localStorage.setItem(storageKey, JSON.stringify(next));
              setPractice(next);
            }}
          /> : <p role="status" className="teaching-muted">没有符合当前条件的案例。</p>}
        </>
      )}
    </div>
  );
}

function CaseExercise({ item, full, onQuestion, onKnowledge, onAbility, onSave }: {
  item: Case;
  full: GraphFull | null;
  onQuestion: (id: string) => void;
  onKnowledge: (id: string) => void;
  onAbility: (id: string) => void;
  onSave: (value: Attempt) => void;
}) {
  const [initial, setInitial] = useState('');
  const [initialLocked, setInitialLocked] = useState(false);
  const [choiceId, setChoiceId] = useState('');
  const [answer, setAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<TeachingReview | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const total = item.rubric.reduce((sum, row) => sum + row.points, 0);
  const scenario = item.scenario;
  const choice = scenario?.choices.find((entry) => entry.id === choiceId);

  const save = (value: Pick<Attempt, 'scores' | 'source' | 'quotes'>) => {
    try {
      onSave({ ...value, initial: initial.trim(), answer: answer.trim(), choice: choiceId, at: Date.now() });
      setStatus('已保存到本浏览器，可在能力图谱查看。');
    } catch {
      setStatus('浏览器无法保存练习记录。');
    }
  };

  async function requestReview() {
    setBusy(true);
    setStatus('');
    try {
      const review = await reviewCase(item.id, answer.trim(), choiceId || undefined);
      setResult(review);
      save({ source: 'ai', scores: Object.fromEntries(review.items.map((row) => [row.id, row.score])),
        quotes: Object.fromEntries(review.items.map((row) => [row.id, row.quote])) });
    } catch (err) {
      setStatus((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="teaching-card">
      <h3>{item.title}</h3>
      <p>{item.context}</p>
      <div className="teaching-table">
        <table>
          <thead><tr>{item.table.columns.map((label) => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>{item.table.rows.map(([label, ...values]) => (
            <tr key={label}><th scope="row">{label}</th>{values.map((value, i) => <td key={i}>{value}</td>)}</tr>
          ))}</tbody>
        </table>
      </div>
      <p><strong>分析任务</strong> {scenario?.initial_prompt ?? item.question}</p>
      {item.refs?.length ? <p className="teaching-muted">课程出处 · {item.refs.join(' · ')}</p> : null}
      {item.reading && <p className="teaching-muted"><a href={item.reading.url} target="_blank" rel="noreferrer">{item.reading.label}</a></p>}
      <div className="teaching-links">
        {full?.nodes.filter((node) => item.kp_ids.includes(node.kp_id ?? '')).map((node) => (
          <button key={node.id} onClick={() => onKnowledge(node.id)}>{node.label}</button>
        ))}
        {full?.questions.filter((question) => item.question_ids.includes(question.qid)).map((question) => (
          <button key={question.qid} title={question.question} onClick={() => onQuestion(question.qid)}>相关问题 {question.qid}</button>
        ))}
      </div>
      {scenario && <div className="teaching-rubric">
        <h3>初判</h3>
        <label className="teaching-answer">你的初步判断
          <textarea value={initial} maxLength={3000} rows={4} readOnly={initialLocked}
            onChange={(event) => setInitial(event.target.value)} placeholder="先写下你已有的结论和理由。" />
        </label>
        {!initialLocked && <button disabled={!initial.trim()} onClick={() => setInitialLocked(true)}>记录初判，选择补充证据</button>}
        {initialLocked && <div className="teaching-rubric">
          <h3>补充证据</h3>
          <p>{scenario.decision_prompt}</p>
          <div className="teaching-links">
            {scenario.choices.map((entry) => <button key={entry.id} disabled={!!choice}
              aria-pressed={choiceId === entry.id} onClick={() => setChoiceId(entry.id)}>{entry.label}</button>)}
          </div>
          {choice && <blockquote className="teaching-document">{choice.evidence}</blockquote>}
        </div>}
      </div>}
      {(!scenario || choice) && <>
      {scenario && <h3 className="teaching-revision">修订结论</h3>}
      {scenario && <p>{scenario.revision_prompt}</p>}
      <label className="teaching-answer">{scenario ? '你的修订作答' : '你的作答'}
        <textarea value={answer} maxLength={6000} rows={5} readOnly={submitted}
          onChange={(event) => setAnswer(event.target.value)} placeholder="写下计算过程、判断依据和结论。" />
      </label>
      <div className="teaching-links">
        {submitted ? (
          <>
            <button disabled={busy || result !== null} onClick={() => void requestReview()}>
              {busy ? '正在评阅…' : '获取模型评阅建议'}
            </button>
            <button disabled={busy} onClick={() => {
              setSubmitted(false);
              setResult(null);
              setScores({});
              setStatus('');
            }}>修改作答</button>
          </>
        ) : <button disabled={!answer.trim()} onClick={() => setSubmitted(true)}>提交并查看量规</button>}
      </div>
      <p role="status" className="teaching-muted">{status}</p>
      </>}
      {submitted && (
        <div className="teaching-rubric">
          <h3>参考评分量规（{total} 分）</h3>
          {scenario && <p>{scenario.debrief}</p>}
          {scenario && choice && <details>
            <summary>对照其他证据路径</summary>
            {scenario.choices.filter((entry) => entry.id !== choice.id).map((entry) => (
              <div key={entry.id}><strong>{entry.label}</strong><p>{entry.evidence}</p></div>
            ))}
          </details>}
          {result && <p>模型建议 {result.total} / {total} 分</p>}
          {item.rubric.map((row) => {
            const grade = result?.items.find((entry) => entry.id === row.id);
            return (
              <div key={row.id} className="teaching-criterion">
                <strong>{row.title} · {row.points} 分</strong>
                <button className="teaching-ability-link" onClick={() => onAbility(row.ability_id)}>查看所考查能力</button>
                <p>{scenario?.criterion_id === row.id && choice ? choice.rubric_note : row.expected}</p>
                {grade && <p>模型建议 {grade.score} 分 · {grade.feedback}
                  {grade.quote && <span>（作答依据「{grade.quote}」）</span>}
                </p>}
                <label>自评分数 <select value={Number.isInteger(scores[row.id]) ? scores[row.id] : ''} onChange={(event) => {
                  const value = event.target.value;
                  setScores((previous) => ({ ...previous, [row.id]: value === '' ? NaN : Number(value) }));
                }}>
                  <option value="">请选择</option>
                  {Array.from({ length: row.points + 1 }, (_, points) => <option key={points}>{points}</option>)}
                </select></label>
              </div>
            );
          })}
          <button disabled={busy || item.rubric.some((row) => !Number.isInteger(scores[row.id]))}
            onClick={() => save({ source: 'self', scores })}>保存自评</button>
          {scenario && <button disabled={busy} onClick={() => {
            setInitialLocked(false);
            setInitial('');
            setChoiceId('');
            setAnswer('');
            setSubmitted(false);
            setScores({});
            setResult(null);
            setStatus('');
          }}>重新推演</button>}
        </div>
      )}
    </section>
  );
}
