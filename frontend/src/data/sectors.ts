import {
  Brain,
  Bot,
  Atom,
  ShieldCheck,
  Rocket,
  Dna,
  Gem,
  Droplets,
} from "lucide-react";

export interface StockPick {
  ticker: string;
  name: string;
  flag: "KR" | "US";
  desc: string;
}

export interface SectorRisk {
  title: string;
  desc: string;
  severity: "high" | "medium" | "low";
}

export interface SectorDef {
  id: string;
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: React.ComponentType<any>;
  emoji: string;
  color: string;
  desc: string;
  curve: number[];
  picks: StockPick[];
  materials: string[];
  risks: SectorRisk[];
  trackingIndicators: string[];
  angle: number;
}

function makeCurve(pts: Record<number, number>): number[] {
  const years = Array.from({ length: 30 }, (_, i) => i + 1);
  const keys = Object.keys(pts).map(Number).sort((a, b) => a - b);
  return years.map((y) => {
    if (pts[y] !== undefined) return pts[y];
    const lo = keys.filter((k) => k <= y).pop()!;
    const hi = keys.find((k) => k >= y)!;
    if (lo === hi) return pts[lo];
    const t = (y - lo) / (hi - lo);
    return pts[lo] + (pts[hi] - pts[lo]) * t;
  });
}

export function normalizeWeights(sectors: SectorDef[], yearIdx: number): Map<string, number> {
  const raw = sectors.map((s) => s.curve[yearIdx]);
  const total = raw.reduce((a, b) => a + b, 0);
  const map = new Map<string, number>();
  sectors.forEach((s, i) => map.set(s.id, total > 0 ? raw[i] / total : 0));
  return map;
}

export const SECTORS: SectorDef[] = [
  {
    id: "ai-semi",
    name: "AI / 반도체",
    icon: Brain,
    emoji: "🧠",
    color: "#3b82f6",
    desc: "AI 혁명의 핵심 인프라. GPU, HBM, 파운드리, EDA 등 반도체 밸류체인 전체가 구조적 성장기.",
    curve: makeCurve({ 1: 0.95, 2: 0.88, 3: 0.70, 4: 0.50, 5: 0.35, 7: 0.20, 10: 0.10, 15: 0.05, 20: 0.03, 25: 0.02, 30: 0.02 }),
    picks: [
      { ticker: "NVDA", name: "NVIDIA", flag: "US", desc: "비중 35% | AI GPU 독점, 매출 YoY +120%, 데이터센터 캡엑스 직접 수혜" },
      { ticker: "TSM", name: "TSMC", flag: "US", desc: "비중 25% | 3nm 독점, NVDA/AAPL/AMD 전량 수탁. 대체 불가" },
      { ticker: "AVGO", name: "Broadcom", flag: "US", desc: "비중 15% | 커스텀 AI칩(Google TPU), 네트워킹 1위, 배당+성장" },
      { ticker: "000660.KS", name: "SK하이닉스", flag: "KR", desc: "비중 15% | HBM 세계 1위, NVDA 독점 공급. 한국 AI 대장주" },
      { ticker: "005930.KS", name: "삼성전자", flag: "KR", desc: "비중 10% | HBM 2위 진입, 파운드리 회복 베팅. 저평가 구간" },
    ],
    materials: ["실리콘 웨이퍼", "네온가스", "금", "구리"],
    risks: [
      { title: "AI 버블 붕괴", desc: "AI 투자 ROI 미달 시 캡엑스 축소 → NVDA 매출 급감", severity: "high" },
      { title: "경쟁 심화", desc: "AMD MI300, Google TPU, 자체칩 트렌드 → NVDA 마진 압박", severity: "medium" },
      { title: "미중 반도체 전쟁", desc: "수출 규제 강화 시 TSMC/SK하이닉스 중국 매출 타격", severity: "high" },
      { title: "공급 과잉", desc: "메모리 사이클 하강 시 SK하이닉스/삼성전자 실적 하락", severity: "medium" },
    ],
    trackingIndicators: ["필라델피아 반도체지수(SOX)", "구리 선물가격", "대만 수출 데이터", "NVDA Forward P/E"],
    angle: 0,
  },
  {
    id: "robotics",
    name: "로봇 / 자동화",
    icon: Bot,
    emoji: "🤖",
    color: "#f59e0b",
    desc: "휴머노이드 로봇, 산업용 자동화, 협동로봇이 제조업/서비스업을 재편. 2030년 로봇 시장 $260B 전망.",
    curve: makeCurve({ 1: 0.50, 2: 0.65, 3: 0.80, 4: 0.85, 5: 0.75, 7: 0.45, 10: 0.20, 15: 0.08, 20: 0.04, 25: 0.03, 30: 0.02 }),
    picks: [
      { ticker: "TSLA", name: "Tesla", flag: "US", desc: "비중 30% | Optimus 2027 양산, FSD 라이센싱. 로봇+자율주행 동시 베팅" },
      { ticker: "ISRG", name: "Intuitive Surgical", flag: "US", desc: "비중 25% | 다빈치 수술로봇 독점, 매출 성장 17%, 경쟁자 없음" },
      { ticker: "454910.KS", name: "두산로보틱스", flag: "KR", desc: "비중 20% | 협동로봇 글로벌 Top5, 한국 로봇 대장주. IPO 후 성장 가속" },
      { ticker: "FANUY", name: "Fanuc", flag: "US", desc: "비중 15% | 산업용 로봇 세계 1위, 공장자동화 필수. 안정적 현금흐름" },
      { ticker: "267250.KS", name: "현대로보틱스", flag: "KR", desc: "비중 10% | 산업용 로봇 국내 1위, 현대차 그룹 시너지. 저평가" },
    ],
    materials: ["리튬", "구리", "희토류", "특수강"],
    risks: [
      { title: "Optimus 양산 지연", desc: "Tesla 로봇 일정 지연 시 로봇 내러티브 전체 냉각", severity: "high" },
      { title: "규제 리스크", desc: "노동법, 안전 규제로 로봇 도입 속도 제한", severity: "medium" },
      { title: "원가 경쟁력", desc: "인건비 대비 로봇 ROI 미달 시 수요 둔화", severity: "medium" },
    ],
    trackingIndicators: ["리튬 가격(LIT ETF)", "구리 선물", "ISM 제조업 PMI", "Tesla Optimus 뉴스"],
    angle: 45,
  },
  {
    id: "smr-nuclear",
    name: "SMR / 원자력",
    icon: Atom,
    emoji: "⚛️",
    color: "#8b5cf6",
    desc: "AI 데이터센터 전력 폭증 + 탄소중립. SMR이 차세대 베이스로드 에너지원으로 부상.",
    curve: makeCurve({ 1: 0.50, 2: 0.55, 3: 0.50, 4: 0.38, 5: 0.25, 7: 0.15, 10: 0.08, 15: 0.04, 20: 0.03, 25: 0.02, 30: 0.02 }),
    picks: [
      { ticker: "CEG", name: "Constellation Energy", flag: "US", desc: "비중 30% | 미국 최대 원전, MS/Google 전력계약. 매출 확정된 성장" },
      { ticker: "CCJ", name: "Cameco", flag: "US", desc: "비중 25% | 우라늄 공급 부족 수혜, 가격 $100/lb 돌파. 원자재 독점" },
      { ticker: "BWXT", name: "BWX Technologies", flag: "US", desc: "비중 20% | SMR 핵심부품, 미 해군 원자로 독점. 방산+에너지" },
      { ticker: "034020.KS", name: "두산에너빌리티", flag: "KR", desc: "비중 15% | 한국 원전 기자재 1위, 체코 수출 수주. K-원전 대표주" },
      { ticker: "015760.KS", name: "한국전력", flag: "KR", desc: "비중 10% | 원전 가동률↑, 전기요금 인상 기대. 턴어라운드 베팅" },
    ],
    materials: ["우라늄", "지르코늄", "특수강", "냉각재"],
    risks: [
      { title: "원전 사고 리스크", desc: "후쿠시마급 사고 발생 시 전 세계 원전 정책 역전", severity: "high" },
      { title: "SMR 기술 지연", desc: "NuScale 등 SMR 프로젝트 일정 지연·비용 초과", severity: "medium" },
      { title: "정책 변동", desc: "정권 교체 시 탈원전 정책 복귀 가능성", severity: "medium" },
      { title: "우라늄 가격 급락", desc: "러시아 우라늄 수출 재개 시 공급 증가 → CCJ 타격", severity: "low" },
    ],
    trackingIndicators: ["우라늄 현물가격(UxC)", "URA ETF", "미국 전력 수요 데이터", "SMR 인허가 진행상황"],
    angle: 90,
  },
  {
    id: "cybersec",
    name: "사이버보안",
    icon: ShieldCheck,
    emoji: "🛡️",
    color: "#ef4444",
    desc: "AI 시대 사이버 위협 기하급수적 증가. 제로트러스트, 클라우드 보안이 필수 인프라로 자리잡음.",
    curve: makeCurve({ 1: 0.15, 2: 0.14, 3: 0.12, 5: 0.10, 7: 0.08, 10: 0.06, 15: 0.05, 20: 0.04, 25: 0.03, 30: 0.03 }),
    picks: [
      { ticker: "CRWD", name: "CrowdStrike", flag: "US", desc: "비중 30% | 엔드포인트 1위, ARR $4B+, AI 위협탐지. 매출 성장 33%" },
      { ticker: "PANW", name: "Palo Alto Networks", flag: "US", desc: "비중 30% | 통합 보안 플랫폼, 3,800개+ 대기업 고객. 마진 확대 중" },
      { ticker: "FTNT", name: "Fortinet", flag: "US", desc: "비중 20% | 차세대 방화벽 1위, OT보안 신성장. 가성비 최고" },
      { ticker: "ZS", name: "Zscaler", flag: "US", desc: "비중 10% | 제로트러스트 퓨어플레이, 클라우드 보안 전환 수혜" },
      { ticker: "S", name: "SentinelOne", flag: "US", desc: "비중 10% | AI 기반 자율보안, 고성장 소형주. 리스크↑ 수익↑" },
    ],
    materials: [],
    risks: [
      { title: "밸류에이션 부담", desc: "CRWD P/S 20배+, 성장 둔화 시 주가 급락 가능", severity: "medium" },
      { title: "AI가 보안 대체", desc: "AI 자동화로 보안 인력·솔루션 수요 감소 가능성", severity: "low" },
      { title: "대형 보안사고", desc: "CrowdStrike 블루스크린 사태(2024) 재발 리스크", severity: "medium" },
    ],
    trackingIndicators: ["BUG ETF(사이버보안)", "기업 IT 지출 전망", "주요 보안사고 빈도", "CRWD ARR 성장률"],
    angle: 135,
  },
  {
    id: "space",
    name: "우주항공",
    icon: Rocket,
    emoji: "🚀",
    color: "#06b6d4",
    desc: "위성 인터넷, 우주 관광, 우주 자원 채굴. 2040년 $1T+ 우주 경제 시대 개막.",
    curve: makeCurve({ 1: 0.03, 2: 0.03, 3: 0.04, 5: 0.06, 7: 0.10, 10: 0.18, 12: 0.30, 15: 0.50, 17: 0.65, 20: 0.75, 22: 0.70, 25: 0.50, 30: 0.30 }),
    picks: [
      { ticker: "RKLB", name: "Rocket Lab", flag: "US", desc: "비중 30% | 소형위성 발사 2위, 시총 $12B. SpaceX 비상장이라 유일한 퓨어플레이" },
      { ticker: "LMT", name: "Lockheed Martin", flag: "US", desc: "비중 25% | GPS위성+우주탐사, 방산 안정성+우주 업사이드. 배당 2.5%" },
      { ticker: "LHX", name: "L3Harris", flag: "US", desc: "비중 20% | 우주 센서+위성통신, 미 국방부 핵심 협력사" },
      { ticker: "047810.KS", name: "한국항공우주", flag: "KR", desc: "비중 15% | KF-21 양산, 해외수출 확대. 한국 방산+우주 대표주" },
      { ticker: "BA", name: "Boeing", flag: "US", desc: "비중 10% | SLS 발사체, Starliner. 턴어라운드 시 폭발력 큼" },
    ],
    materials: ["티타늄", "카본파이버", "희토류"],
    risks: [
      { title: "발사 실패", desc: "로켓 폭발 시 RKLB 주가 30%+ 급락 가능", severity: "high" },
      { title: "SpaceX 독점", desc: "SpaceX가 시장 독식하면 RKLB 등 경쟁사 도태", severity: "high" },
      { title: "정부 예산 삭감", desc: "NASA/방산 예산 삭감 시 수주 감소", severity: "medium" },
      { title: "장기 적자 지속", desc: "우주기업 대부분 적자, 자금조달 실패 시 파산", severity: "high" },
    ],
    trackingIndicators: ["UFO ETF(우주)", "미국 국방부 예산", "위성 발사 횟수", "SpaceX Starlink 가입자"],
    angle: 180,
  },
  {
    id: "biotech",
    name: "생명공학",
    icon: Dna,
    emoji: "🧬",
    color: "#22c55e",
    desc: "유전자 치료, mRNA, CRISPR 유전자 편집. 고령화 시대 바이오가 헬스케어를 혁신.",
    curve: makeCurve({ 1: 0.18, 2: 0.22, 3: 0.30, 5: 0.50, 7: 0.65, 9: 0.70, 10: 0.60, 12: 0.45, 15: 0.25, 20: 0.10, 25: 0.05, 30: 0.03 }),
    picks: [
      { ticker: "CRSP", name: "CRISPR Therapeutics", flag: "US", desc: "비중 30% | 유전자편집 1위, 시총 $4B. 적응증 확대 시 10배+. 최고 수익 잠재력" },
      { ticker: "LLY", name: "Eli Lilly", flag: "US", desc: "비중 25% | 비만약 시장 $100B, 알츠하이머 신약. 안정+성장 겸비" },
      { ticker: "ILMN", name: "Illumina", flag: "US", desc: "비중 20% | 유전체 시퀀싱 독점, 비용 하락 → 수요 폭발 수혜" },
      { ticker: "207940.KS", name: "삼성바이오로직스", flag: "KR", desc: "비중 15% | 세계 최대 바이오CDMO, 수주잔고 역대 최대. K-바이오 대장" },
      { ticker: "068270.KS", name: "셀트리온", flag: "KR", desc: "비중 10% | 바이오시밀러 글로벌 Top3, 짐펜트라 미국 매출 급증" },
    ],
    materials: ["세포배양 소재", "원료의약품", "플라스미드 DNA"],
    risks: [
      { title: "임상 실패", desc: "CRISPR 임상 3상 실패 시 주가 50%+ 급락. 바이오 최대 리스크", severity: "high" },
      { title: "FDA 규제 강화", desc: "유전자치료 안전성 이슈 시 승인 지연·반려", severity: "high" },
      { title: "LLY 비만약 경쟁", desc: "노보노디스크, 화이자 비만약 경쟁 → LLY 점유율 하락", severity: "medium" },
      { title: "바이오시밀러 가격전쟁", desc: "셀트리온 마진 압박, 가격 인하 경쟁 심화", severity: "medium" },
    ],
    trackingIndicators: ["XBI ETF(바이오텍)", "FDA 승인 일정", "GLP-1 처방 데이터", "삼성바이오 수주잔고"],
    angle: 225,
  },
  {
    id: "quantum",
    name: "양자컴퓨팅",
    icon: Gem,
    emoji: "💎",
    color: "#a855f7",
    desc: "기존 슈퍼컴퓨터 한계를 초월. 신약 개발, 암호, 최적화 문제의 게임체인저.",
    curve: makeCurve({ 1: 0.02, 2: 0.02, 3: 0.02, 5: 0.03, 7: 0.05, 10: 0.10, 12: 0.18, 15: 0.35, 17: 0.55, 20: 0.75, 22: 0.80, 25: 0.65, 28: 0.40, 30: 0.25 }),
    picks: [
      { ticker: "IONQ", name: "IonQ", flag: "US", desc: "비중 30% | 이온트랩 1위, 시총 $9B/매출 $40M. 초고위험 초고수익" },
      { ticker: "GOOG", name: "Alphabet", flag: "US", desc: "비중 25% | Willow 양자칩, 검색+AI+양자 3중 업사이드. 안전한 양자 베팅" },
      { ticker: "IBM", name: "IBM", flag: "US", desc: "비중 20% | 1000+ 큐비트, 기업용 양자 선두. 배당+양자 옵션" },
      { ticker: "RGTI", name: "Rigetti Computing", flag: "US", desc: "비중 15% | 초전도 양자프로세서, 시총 $3B. IONQ 대안. 순수 베팅" },
      { ticker: "MSFT", name: "Microsoft", flag: "US", desc: "비중 10% | Azure 양자 클라우드, 위상학적 큐비트. 대형주 양자 옵션" },
    ],
    materials: ["초전도체", "헬륨-3", "다이아몬드 NV 센터"],
    risks: [
      { title: "기술 정체", desc: "오류 보정 문제 미해결 시 상용화 10년+ 추가 지연", severity: "high" },
      { title: "기업 파산", desc: "IONQ/RGTI 적자 지속, 자금 소진 시 상장폐지", severity: "high" },
      { title: "대안 기술 등장", desc: "고전 컴퓨팅 발전이 양자 필요성 약화", severity: "medium" },
    ],
    trackingIndicators: ["IONQ 매출/큐비트 수", "IBM 양자 로드맵 진척", "양자 논문 발표 빈도", "QTUM ETF"],
    angle: 270,
  },
  {
    id: "hydrogen",
    name: "수소 / 에너지",
    icon: Droplets,
    emoji: "💧",
    color: "#14b8a6",
    desc: "그린수소가 궁극적 청정에너지. 철강/화학/운송 탈탄소화의 핵심 솔루션.",
    curve: makeCurve({ 1: 0.02, 2: 0.02, 3: 0.03, 5: 0.05, 7: 0.10, 10: 0.25, 12: 0.42, 15: 0.55, 17: 0.50, 20: 0.35, 25: 0.18, 30: 0.10 }),
    picks: [
      { ticker: "BE", name: "Bloom Energy", flag: "US", desc: "비중 30% | SOFC 연료전지 1위, AI 데이터센터 전력 계약. 흑자 근접" },
      { ticker: "PLUG", name: "Plug Power", flag: "US", desc: "비중 20% | 그린수소 생태계 통합, 대형 계약. 적자지만 성장률 최고" },
      { ticker: "ENPH", name: "Enphase Energy", flag: "US", desc: "비중 20% | 태양광 마이크로인버터 1위, 에너지저장 확대. 마진 40%+" },
      { ticker: "005380.KS", name: "현대자동차", flag: "KR", desc: "비중 20% | 넥쏘 수소차, 수소연료전지 시스템. 완성차+수소 동시 베팅" },
      { ticker: "336260.KS", name: "두산퓨얼셀", flag: "KR", desc: "비중 10% | 발전용 연료전지 국내 1위, 정부 수소정책 직접 수혜" },
    ],
    materials: ["백금", "이리듐", "전해질 멤브레인"],
    risks: [
      { title: "경제성 미확보", desc: "그린수소 $5/kg → $2/kg 목표 미달 시 수요 없음", severity: "high" },
      { title: "PLUG 파산 리스크", desc: "적자 지속, 현금 소진 속도 빠름. 추가 유상증자 가능", severity: "high" },
      { title: "정책 변동", desc: "미국 IRA 보조금 축소/폐지 시 경제성 붕괴", severity: "high" },
      { title: "배터리 EV와 경쟁", desc: "배터리 가격 하락이 수소차 수요를 잠식", severity: "medium" },
    ],
    trackingIndicators: ["수소 가격($/kg)", "백금 선물", "ICLN ETF(클린에너지)", "미국 IRA 보조금 집행"],
    angle: 315,
  },
];
