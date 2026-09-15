/**
 * Startup Valuation Master Tool Engine
 * Based on Startup_Valuation_Master_All_Methods_and_Cases.xlsx
 * Fully reactive calculation suite with 7 interlinked valuation models,
 * 2D sensitivity tables, and liquidation preference waterfall simulation.
 */

const ValuationEngine = (() => {
    // -------------------------------------------------------------
    // Benchmark Default States (from Excel Workbook)
    // -------------------------------------------------------------
    const getBenchmarkData = () => ({
        m1: {
            baseline: 30, // 억원
            scorecard: [
                { id: 'team', name: '창업팀 역량 및 리더십 (Team Quality)', weight: 0.30, score: 1.40, reason: '빅테크 AI 엔지니어 및 연속 창업자 출신 구성 (최우수)' },
                { id: 'market', name: '기회 규모 및 TAM 시장성 (Opportunity Size)', weight: 0.25, score: 1.20, reason: '글로벌 GenAI B2B 생산성 도구 시장 고성장' },
                { id: 'product', name: '제품 및 독점 기술력 (Product / IP)', weight: 0.15, score: 1.10, reason: '자체 온디바이스 경량화 SLM 특허 및 MVP 출시' },
                { id: 'moat', name: '경쟁 환경 및 해자 (Competitive Moat)', weight: 0.10, score: 0.90, reason: '빅테크의 번들링 위협 상존 (보통 이하)' },
                { id: 'gtm', name: '마케팅 및 파트너십 (Go-to-Market)', weight: 0.10, score: 1.15, reason: '국내외 주요 SaaS 유통 채널과의 전략적 제휴 진행' },
                { id: 'capital', name: '추가 투자유치 필요성 (Capital Requirement)', weight: 0.05, score: 1.00, reason: '시드 라운드 목표 5억 원으로 적정 수준' },
                { id: 'traction', name: '기타 피드백 및 트랙션 (Feedback / Traction)', weight: 0.05, score: 1.30, reason: '비공개 베타 고객 1,000명 확보 및 높은 리텐션' }
            ],
            berkus: [
                { id: 'idea', name: '기본 아이디어 건전성 (Sound Idea)', maxCap: 7, achieved: 0.90, note: 'AI 워크플로우 자동화 분야로 시장 니즈 명확' },
                { id: 'prototype', name: '프로토타입 / 기술 위험 제거 (Prototype)', maxCap: 7, achieved: 0.85, note: 'PoC 테스트 완료, 모델 응답 속도 최적화 성공' },
                { id: 'management', name: '우수한 경영진 역량 (Quality Management)', maxCap: 7, achieved: 1.00, note: '팀 전원 AI 전공 석박사 및 풀스택 개발 역량 보유' },
                { id: 'alliances', name: '전략적 제휴 및 파트너십 (Strategic Alliances)', maxCap: 7, achieved: 0.60, note: '클라우드 서비스사 파트너 등록 (초기 협의 단계)' },
                { id: 'sales', name: '제품 출시 및 초기 매출 견인 (Product Rollout / Sales)', maxCap: 7, achieved: 0.50, note: '베타 버전 런칭, 유료 구독 전환 테스트 중' }
            ]
        },
        m2: {
            investment: 100, // 억원
            holdingYears: 5, // 년
            targetIRR: 0.30, // 30%
            exitRevenue: 800, // 억원
            exitNetIncome: 150, // 억원
            targetPER: 25, // 25배
            dilution: 0.40 // 40%
        },
        m3: {
            currentARR: 120, // 억원
            forwardARR: 250, // 억원
            nrr: 1.35, // 135%
            fcfMargin: -0.15, // -15%
            grossMargin: 0.72, // 72%
            peerMultiple: 8.5, // 8.5배
            r40Coeff: 0.08, // 0.08x/pt
            nrrCoeff: 0.15, // 0.15x/pt
            netDebt: -80 // 순차입금 -80억 (순현금 80억)
        },
        m4: {
            best: { prob: 0.20, rev5: 2000, fcf5: 450, g: 0.04, wacc: 0.18, fcfs: [-80, -30, 100, 260, 450] },
            base: { prob: 0.55, rev5: 800, fcf5: 140, g: 0.03, wacc: 0.20, fcfs: [-60, -40, 20, 80, 140] },
            failure: { prob: 0.25, rev5: 100, fcf5: -30, g: 0.00, wacc: 0.25, fcfs: [-40, -50, -30, -20, -30], tv: 30 }
        },
        m5: {
            wacc: 0.18,
            loUpfront: 300,
            loMilestones: 700,
            peakSales: 5000,
            royaltyRate: 0.10,
            bridgePlatform: 150,
            bridgeCash: 120,
            bridgeDebt: -20,
            timeline: [
                { year: 1, event: '임상 1상 개시 및 환자 모집', cf: -50, pos: 1.00 },
                { year: 2, event: '임상 1상 데이터 분석 및 종료', cf: -50, pos: 1.00 },
                { year: 3, event: '임상 2상 진입 (용량 설정 시험)', cf: -150, pos: 0.60 },
                { year: 4, event: '임상 2상 환자 투약 진행', cf: -150, pos: 0.60 },
                { year: 5, event: '2상 완료 & 빅파마 L/O 계약금 유입', cf: 150, pos: 0.60 },
                { year: 6, event: '임상 3상 진입 마일스톤 수령', cf: 200, pos: 0.21 },
                { year: 7, event: '임상 3상 진행 (빅파마 비용 전담)', cf: 0, pos: 0.21 },
                { year: 8, event: 'FDA NDA 품목허가 신청 마일스톤', cf: 200, pos: 0.21 },
                { year: 9, event: 'FDA 품목허가 승인 완료 마일스톤', cf: 300, pos: 0.126 },
                { year: 10, event: '글로벌 상용화 시판 및 로열티 수령', cf: 500, pos: 0.1071 }
            ]
        },
        m6: {
            sotp: [
                { id: 'sw', name: 'Enterprise GenAI 플랫폼 (SW)', metricName: 'Forward ARR', value: 800, multiple: 15, base: 'EV / ARR', peer: '글로벌 B2B SaaS Peer 평균' },
                { id: 'hw', name: '온디바이스 AI 칩 및 모듈 (HW)', metricName: '차년도 순이익', value: 300, multiple: 25, base: 'PER', peer: 'AI 팹리스 및 NPU 상장사' },
                { id: 'si', name: 'AI 솔루션 컨설팅 & SI (Services)', metricName: '연간 EBITDA', value: 200, multiple: 10, base: 'EV / EBITDA', peer: '글로벌 IT 서비스 상장사' },
                { id: 're', name: '비영업용 본사 보유 부동산', metricName: '감정평가액', value: 500, multiple: 1, base: 'Book Value', peer: '시가 감정평가액 100% 인정' }
            ],
            waterfall: {
                exitValuation: 15000, // 1조 5,000억원
                classes: [
                    { id: 'c', name: 'Series C 우선주 (Late-stage)', investment: 2000, prefType: 'non_participating', prefMult: 1.0, ownership: 0.15 },
                    { id: 'b', name: 'Series B 우선주 (Growth)', investment: 1000, prefType: 'participating', prefMult: 1.0, ownership: 0.10 },
                    { id: 'a', name: 'Series A 우선주 (Early)', investment: 500, prefType: 'participating', prefMult: 1.0, ownership: 0.10 },
                    { id: 'common', name: '창업자 및 보통주 (Common)', investment: 50, prefType: 'common', prefMult: 0, ownership: 0.65 }
                ]
            }
        }
    });

    let state = getBenchmarkData();

    // -------------------------------------------------------------
    // Helper Formatters
    // -------------------------------------------------------------
    const formatNumber = (num, decimals = 1) => {
        if (num === null || num === undefined || isNaN(num)) return '-';
        return Number(num).toLocaleString('ko-KR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    };

    const formatCurrency = (val, unit = '억원', decimals = 1) => {
        if (val === null || val === undefined || isNaN(val)) return '-';
        return `${formatNumber(val, decimals)} ${unit}`;
    };

    const formatPercent = (val, decimals = 1) => {
        if (val === null || val === undefined || isNaN(val)) return '-';
        return `${(val * 100).toFixed(decimals)}%`;
    };

    // -------------------------------------------------------------
    // Model 1: Scorecard & Berkus Calculations
    // -------------------------------------------------------------
    const calculateM1 = () => {
        const baseline = Number(state.m1.baseline) || 30;

        // Scorecard Method
        let totalScorecardMultiplier = 0;
        const scorecardRows = state.m1.scorecard.map(item => {
            const mult = item.weight * item.score;
            const contrib = mult * baseline;
            totalScorecardMultiplier += mult;
            return { ...item, mult, contrib };
        });
        const scorecardPreMoney = totalScorecardMultiplier * baseline;

        // Berkus Method
        let totalBerkusMax = 0;
        let totalBerkusPreMoney = 0;
        const berkusRows = state.m1.berkus.map(item => {
            const val = item.maxCap * item.achieved;
            totalBerkusMax += item.maxCap;
            totalBerkusPreMoney += val;
            return { ...item, val };
        });

        // Combined Average
        const combinedAveragePreMoney = (scorecardPreMoney + totalBerkusPreMoney) / 2;

        return {
            baseline,
            scorecardRows,
            totalScorecardMultiplier,
            scorecardPreMoney,
            berkusRows,
            totalBerkusMax,
            totalBerkusPreMoney,
            combinedAveragePreMoney
        };
    };

    // -------------------------------------------------------------
    // Model 2: VC Method (DeepTech) Calculations
    // -------------------------------------------------------------
    const calculateM2 = () => {
        const { investment, holdingYears, targetIRR, exitRevenue, exitNetIncome, targetPER, dilution } = state.m2;

        // Step 1: Terminal Value = Exit Net Income * Target PER
        const terminalValue = exitNetIncome * targetPER;

        // Step 2: Target Multiple = (1 + targetIRR) ^ holdingYears
        const targetMultiple = Math.pow(1 + targetIRR, holdingYears);

        // Step 3: Diluted TV = Terminal Value * (1 - dilution)
        const dilutedTV = terminalValue * (1 - dilution);

        // Step 4: Post-money = Diluted TV / Target Multiple
        const postMoney = targetMultiple > 0 ? dilutedTV / targetMultiple : 0;

        // Step 5: Pre-money = Post-money - investment
        const preMoney = postMoney - investment;

        // Step 6: Acquired ownership = investment / postMoney
        const acquiredShare = postMoney > 0 ? investment / postMoney : 0;

        // Step 7: Exit ownership = acquiredShare * (1 - dilution)
        const exitShare = acquiredShare * (1 - dilution);

        // Step 8: Exit Cash Flow = Terminal Value * exitShare
        const exitCashFlow = terminalValue * exitShare;

        // 2D Sensitivity Matrix: Dilution vs IRR
        const dilutionRange = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50];
        const irrRange = [0.20, 0.25, 0.30, 0.35, 0.40];

        const sensitivityMatrix = dilutionRange.map(d => {
            const rowValues = irrRange.map(irr => {
                const mult = Math.pow(1 + irr, holdingYears);
                const dTV = terminalValue * (1 - d);
                const post = mult > 0 ? dTV / mult : 0;
                const pre = post - investment;
                return {
                    dilution: d,
                    irr: irr,
                    preMoney: pre,
                    isActive: Math.abs(d - dilution) < 0.001 && Math.abs(irr - targetIRR) < 0.001
                };
            });
            return { dilution: d, values: rowValues };
        });

        return {
            investment,
            holdingYears,
            targetIRR,
            exitRevenue,
            exitNetIncome,
            targetPER,
            dilution,
            terminalValue,
            targetMultiple,
            dilutedTV,
            postMoney,
            preMoney,
            acquiredShare,
            exitShare,
            exitCashFlow,
            irrRange,
            dilutionRange,
            sensitivityMatrix
        };
    };

    // -------------------------------------------------------------
    // Model 3: Forward Multiples & Rule of 40 (SaaS) Calculations
    // -------------------------------------------------------------
    const calculateM3 = () => {
        const { currentARR, forwardARR, nrr, fcfMargin, grossMargin, peerMultiple, r40Coeff, nrrCoeff, netDebt } = state.m3;

        // 1. YoY Revenue Growth Rate = (forwardARR / currentARR) - 1
        const yoyGrowth = currentARR > 0 ? (forwardARR / currentARR) - 1 : 0;

        // 2. Rule of 40 Score = Growth Rate + FCF Margin
        const r40Score = yoyGrowth + fcfMargin;

        // 3. Rule of 40 Premium Multiple = MAX(0, (r40Score - 0.40) * 100) * r40Coeff
        const r40ExcessPoints = Math.max(0, (r40Score - 0.40) * 100);
        const r40Premium = r40ExcessPoints * r40Coeff;

        // 4. NRR Premium Multiple = MAX(0, (nrr - 1.00) * 100) * nrrCoeff
        const nrrExcessPoints = Math.max(0, (nrr - 1.00) * 100);
        const nrrPremium = nrrExcessPoints * nrrCoeff;

        // 5. Final EV/ARR Multiple = peerMultiple + r40Premium + nrrPremium
        const finalMultiple = peerMultiple + r40Premium + nrrPremium;

        // 6. Enterprise Value (EV) = forwardARR * finalMultiple
        const enterpriseValue = forwardARR * finalMultiple;

        // 7. Equity Value = EV - netDebt
        const equityValue = enterpriseValue - netDebt;

        // 2D Sensitivity Matrix: Forward ARR vs Multiple
        const arrRange = [180, 210, 250, 300, 350];
        const multRange = [12.0, 14.0, 16.0, Number(finalMultiple.toFixed(2)), 20.0, 22.0];
        // Ensure sorted and unique
        const uniqueMultRange = Array.from(new Set(multRange)).sort((a, b) => a - b);

        const sensitivityMatrix = uniqueMultRange.map(m => {
            const rowValues = arrRange.map(arr => {
                const eqVal = arr * m - netDebt;
                return {
                    multiple: m,
                    arr: arr,
                    equityValue: eqVal,
                    isActive: Math.abs(arr - forwardARR) < 1 && Math.abs(m - finalMultiple) < 0.1
                };
            });
            return { multiple: m, values: rowValues };
        });

        return {
            currentARR,
            forwardARR,
            yoyGrowth,
            nrr,
            fcfMargin,
            grossMargin,
            peerMultiple,
            r40Score,
            r40Premium,
            nrrPremium,
            finalMultiple,
            enterpriseValue,
            netDebt,
            equityValue,
            arrRange,
            uniqueMultRange,
            sensitivityMatrix
        };
    };

    // -------------------------------------------------------------
    // Model 4: First Chicago Scenario DCF Calculations
    // -------------------------------------------------------------
    const calculateM4 = () => {
        const { best, base, failure } = state.m4;

        const calcScenarioNPV = (sc, isFailure = false) => {
            const { wacc, g, fcfs } = sc;
            let tv = 0;
            if (isFailure) {
                tv = sc.tv || 30;
            } else {
                const y5fcf = fcfs[fcfs.length - 1];
                tv = wacc > g ? (y5fcf * (1 + g)) / (wacc - g) : 0;
            }

            // DCF sum
            let pvFCF = 0;
            fcfs.forEach((fcf, idx) => {
                const year = idx + 1;
                pvFCF += fcf / Math.pow(1 + wacc, year);
            });
            const pvTV = tv / Math.pow(1 + wacc, fcfs.length);
            const npv = pvFCF + pvTV;

            return { tv, pvFCF, pvTV, npv };
        };

        const bestResult = { ...best, ...calcScenarioNPV(best, false) };
        const baseResult = { ...base, ...calcScenarioNPV(base, false) };
        const failureResult = { ...failure, ...calcScenarioNPV(failure, true) };

        // Weighted Expected Enterprise Value
        const weightedBest = bestResult.npv * bestResult.prob;
        const weightedBase = baseResult.npv * baseResult.prob;
        const weightedFailure = failureResult.npv * failureResult.prob;
        const firstChicagoEV = weightedBest + weightedBase + weightedFailure;

        return {
            best: bestResult,
            base: baseResult,
            failure: failureResult,
            weightedBest,
            weightedBase,
            weightedFailure,
            firstChicagoEV
        };
    };

    // -------------------------------------------------------------
    // Model 5: BioTech rNPV Calculations
    // -------------------------------------------------------------
    const calculateM5 = () => {
        const { wacc, timeline, bridgePlatform, bridgeCash, bridgeDebt } = state.m5;

        let cumPOS = 1.0;
        let cumRNPV = 0;
        const calculatedTimeline = timeline.map(row => {
            const nominalCF = row.cf;
            const pos = row.pos;
            const riskAdjCF = nominalCF * pos;
            const discountFactor = 1 / Math.pow(1 + wacc, row.year);
            const discountedRNPV = riskAdjCF * discountFactor;
            cumRNPV += discountedRNPV;

            return {
                ...row,
                nominalCF,
                riskAdjCF,
                discountFactor,
                discountedRNPV,
                cumRNPV
            };
        });

        const totalNominalCF = calculatedTimeline.reduce((acc, r) => acc + r.nominalCF, 0);
        const totalRiskAdjCF = calculatedTimeline.reduce((acc, r) => acc + r.riskAdjCF, 0);
        const totalPipelineRNPV = calculatedTimeline.reduce((acc, r) => acc + r.discountedRNPV, 0);

        // Bridge to Equity Value
        const finalEquityValue = totalPipelineRNPV + bridgePlatform + bridgeCash + bridgeDebt;

        return {
            wacc,
            timeline: calculatedTimeline,
            totalNominalCF,
            totalRiskAdjCF,
            totalPipelineRNPV,
            bridgePlatform,
            bridgeCash,
            bridgeDebt,
            finalEquityValue
        };
    };

    // -------------------------------------------------------------
    // Model 6: Unicorn SOTP & Liquidation Preference Waterfall
    // -------------------------------------------------------------
    const calculateM6 = () => {
        // 1. SOTP Valuation
        const sotpRows = state.m6.sotp.map(row => {
            const ev = row.value * row.multiple;
            return { ...row, ev };
        });
        const totalSOTPValue = sotpRows.reduce((acc, r) => acc + r.ev, 0);

        // 2. Liquidation Preference Waterfall
        const exitValuation = Number(state.m6.waterfall.exitValuation) || 15000;
        const classes = state.m6.waterfall.classes;

        // Series C check: 1x Non-participating
        // If conversion value (exitValuation * ownership) >= preference (investment * prefMult),
        // Series C CONVERTS to common stock and receives common pro-rata!
        // Otherwise, Series C exercises preference!
        const seriesC = classes.find(c => c.id === 'c');
        const seriesB = classes.find(c => c.id === 'b');
        const seriesA = classes.find(c => c.id === 'a');
        const common = classes.find(c => c.id === 'common');

        const seriesCPref = seriesC.investment * seriesC.prefMult;
        const seriesCAsCommon = exitValuation * seriesC.ownership;
        const seriesCConverts = seriesCAsCommon >= seriesCPref;

        let step1SeriesC = 0;
        let step2SeriesC = 0;
        let totalSeriesC = 0;

        let step1SeriesB = seriesB.investment * seriesB.prefMult;
        let step1SeriesA = seriesA.investment * seriesA.prefMult;
        let step1Common = 0;

        let remainingExit = exitValuation;

        if (seriesCConverts) {
            // Series C converts to common. In step 1: receives 0 preference.
            // Series C receives full 15% of exit valuation (or pro-rata) in common distribution.
            step1SeriesC = 0;
            totalSeriesC = seriesCAsCommon;
            // Participating remaining pool:
            // Remaining after Series B/A preferences:
            const poolAfterBA = Math.max(0, exitValuation - step1SeriesB - step1SeriesA - totalSeriesC);
            // Non-converted common pool: Series B (10%), Series A (10%), Common (65%) = sum 85%
            const sumOtherOwnership = seriesB.ownership + seriesA.ownership + common.ownership;

            const step2SeriesB = sumOtherOwnership > 0 ? (poolAfterBA * seriesB.ownership) / sumOtherOwnership : 0;
            const step2SeriesA = sumOtherOwnership > 0 ? (poolAfterBA * seriesA.ownership) / sumOtherOwnership : 0;
            const step2Common = sumOtherOwnership > 0 ? (poolAfterBA * common.ownership) / sumOtherOwnership : 0;

            const totalSeriesB = step1SeriesB + step2SeriesB;
            const totalSeriesA = step1SeriesA + step2SeriesA;
            const totalCommon = step1Common + step2Common;

            const waterfallRows = [
                { ...seriesC, step1Pref: 0, converted: true, step2Dist: totalSeriesC, totalPayout: totalSeriesC, moic: seriesC.investment > 0 ? totalSeriesC / seriesC.investment : 0 },
                { ...seriesB, step1Pref: step1SeriesB, converted: false, step2Dist: step2SeriesB, totalPayout: totalSeriesB, moic: seriesB.investment > 0 ? totalSeriesB / seriesB.investment : 0 },
                { ...seriesA, step1Pref: step1SeriesA, converted: false, step2Dist: step2SeriesA, totalPayout: totalSeriesA, moic: seriesA.investment > 0 ? totalSeriesA / seriesA.investment : 0 },
                { ...common, step1Pref: 0, converted: false, step2Dist: step2Common, totalPayout: totalCommon, moic: common.investment > 0 ? totalCommon / common.investment : 0 }
            ];

            return {
                sotpRows,
                totalSOTPValue,
                exitValuation,
                seriesCConverts,
                waterfallRows,
                totalPayoutSum: totalSeriesC + totalSeriesB + totalSeriesA + totalCommon
            };
        } else {
            // Series C exercises 1x liquidation preference!
            step1SeriesC = Math.min(exitValuation, seriesCPref);
            remainingExit = Math.max(0, exitValuation - step1SeriesC);

            step1SeriesB = Math.min(remainingExit, seriesB.investment * seriesB.prefMult);
            remainingExit = Math.max(0, remainingExit - step1SeriesB);

            step1SeriesA = Math.min(remainingExit, seriesA.investment * seriesA.prefMult);
            remainingExit = Math.max(0, remainingExit - step1SeriesA);

            // Series C is non-participating, so it does not participate in step 2.
            const sumOtherOwnership = seriesB.ownership + seriesA.ownership + common.ownership;
            const step2SeriesB = sumOtherOwnership > 0 ? (remainingExit * seriesB.ownership) / sumOtherOwnership : 0;
            const step2SeriesA = sumOtherOwnership > 0 ? (remainingExit * seriesA.ownership) / sumOtherOwnership : 0;
            const step2Common = sumOtherOwnership > 0 ? (remainingExit * common.ownership) / sumOtherOwnership : 0;

            const totalSeriesCVal = step1SeriesC;
            const totalSeriesBVal = step1SeriesB + step2SeriesB;
            const totalSeriesAVal = step1SeriesA + step2SeriesA;
            const totalCommonVal = step1Common + step2Common;

            const waterfallRows = [
                { ...seriesC, step1Pref: step1SeriesC, converted: false, step2Dist: 0, totalPayout: totalSeriesCVal, moic: seriesC.investment > 0 ? totalSeriesCVal / seriesC.investment : 0 },
                { ...seriesB, step1Pref: step1SeriesB, converted: false, step2Dist: step2SeriesB, totalPayout: totalSeriesBVal, moic: seriesB.investment > 0 ? totalSeriesBVal / seriesB.investment : 0 },
                { ...seriesA, step1Pref: step1SeriesA, converted: false, step2Dist: step2SeriesA, totalPayout: totalSeriesAVal, moic: seriesA.investment > 0 ? totalSeriesAVal / seriesA.investment : 0 },
                { ...common, step1Pref: 0, converted: false, step2Dist: step2CommonVal, totalPayout: totalCommonVal, moic: common.investment > 0 ? totalCommonVal / common.investment : 0 }
            ];

            return {
                sotpRows,
                totalSOTPValue,
                exitValuation,
                seriesCConverts,
                waterfallRows,
                totalPayoutSum: totalSeriesCVal + totalSeriesBVal + totalSeriesAVal + totalCommonVal
            };
        }
    };

    // -------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------
    return {
        getState: () => state,
        setState: (newState) => { state = newState; },
        resetToBenchmark: () => {
            state = getBenchmarkData();
        },
        calculateM1,
        calculateM2,
        calculateM3,
        calculateM4,
        calculateM5,
        calculateM6,
        formatCurrency,
        formatPercent,
        formatNumber
    };
})();

// -----------------------------------------------------------------
// UI Controller for Startup Valuation Modal
// -----------------------------------------------------------------
const ValuationUI = (() => {
    let currentTab = 'overview';

    const init = () => {
        setupEventListeners();
        renderActiveTab();
    };

    const setupEventListeners = () => {
        // Modal Open / Close
        const btnValuation = document.getElementById('btn-valuation');
        const modal = document.getElementById('valuation-modal');
        const btnClose = document.getElementById('btn-close-valuation');
        const btnReset = document.getElementById('btn-reset-valuation');
        const btnPrint = document.getElementById('btn-print-valuation');
        const btnDownload = document.getElementById('btn-download-valuation-excel');

        if (btnValuation && modal) {
            btnValuation.addEventListener('click', () => {
                modal.style.display = 'flex';
                renderActiveTab();
            });
        }

        if (btnClose && modal) {
            btnClose.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.style.display = 'none';
            });
        }

        if (btnReset) {
            btnReset.addEventListener('click', () => {
                if (confirm('모든 입력값을 엑셀 원본 벤치마크 기본값으로 복원하시겠습니까?')) {
                    ValuationEngine.resetToBenchmark();
                    renderActiveTab();
                }
            });
        }

        // Valuation Report Actions
        const btnGenReport = document.getElementById('btn-generate-val-report');
        const btnDirectPdf = document.getElementById('btn-direct-pdf-valuation');
        const btnDirectWord = document.getElementById('btn-direct-word-valuation');
        const reportModal = document.getElementById('val-report-modal');
        const btnCloseReport = document.getElementById('btn-close-val-report');
        const btnReportPrint = document.getElementById('btn-val-report-print');
        const btnReportWord = document.getElementById('btn-val-report-word');

        if (btnGenReport) {
            btnGenReport.addEventListener('click', () => {
                openReportModal();
            });
        }

        if (btnDirectPdf) {
            btnDirectPdf.addEventListener('click', () => {
                exportValuationToPDF();
            });
        }

        if (btnDirectWord) {
            btnDirectWord.addEventListener('click', () => {
                exportValuationToWord();
            });
        }

        if (btnReportPrint) {
            btnReportPrint.addEventListener('click', () => {
                exportValuationToPDF();
            });
        }

        if (btnReportWord) {
            btnReportWord.addEventListener('click', () => {
                exportValuationToWord();
            });
        }

        if (btnCloseReport && reportModal) {
            btnCloseReport.addEventListener('click', () => {
                reportModal.style.display = 'none';
            });
        }

        if (reportModal) {
            reportModal.addEventListener('click', (e) => {
                if (e.target === reportModal) reportModal.style.display = 'none';
            });
        }

        // Tab Switching
        const tabBtns = document.querySelectorAll('.val-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentTab = btn.dataset.tab;
                renderActiveTab();
            });
        });
    };

    const renderActiveTab = () => {
        const container = document.getElementById('val-tab-content');
        if (!container) return;

        switch (currentTab) {
            case 'overview':
                renderOverview(container);
                break;
            case 'm1':
                renderM1(container);
                break;
            case 'm2':
                renderM2(container);
                break;
            case 'm3':
                renderM3(container);
                break;
            case 'm4':
                renderM4(container);
                break;
            case 'm5':
                renderM5(container);
                break;
            case 'm6':
                renderM6(container);
                break;
            default:
                renderOverview(container);
        }
    };

    // -------------------------------------------------------------
    // Tab 1: Master Overview & Selection Guide
    // -------------------------------------------------------------
    const renderOverview = (container) => {
        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>🗺️ 1. 스타트업 밸류에이션 총괄 맵 & 기법 선택 가이드</h2>
                    <p class="subtitle">투자 라운드, 성장 단계, 산업 특성에 따른 6대 밸류에이션 기법의 핵심 로직과 선택 기준 매트릭스</p>
                </div>
            </div>

            <!-- 대화형 밸류에이션 추천기 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem; border-color: rgba(59, 130, 246, 0.4);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
                    <span style="font-size: 1.5rem;">🤖</span>
                    <h3 style="margin: 0; color: #60a5fa;">대화형 밸류에이션 기법 추천기 (Interactive Valuation Guide)</h3>
                </div>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                    <div style="flex: 1; min-width: 220px;">
                        <label style="font-size: 0.85rem; color: #94a3b8; display: block; margin-bottom: 5px;">1. 투자 대상 라운드 선택</label>
                        <select id="guide-round-select" class="val-select">
                            <option value="seed">Pre-Seed ~ Seed (매출 전 극초기)</option>
                            <option value="seriesA">Series A (초기 매출, PMF 검증)</option>
                            <option value="seriesB">Series B ~ C (스케일업, ARR 100억+)</option>
                            <option value="preIpo">Pre-IPO / 유니콘 (BEP 달성, 복합 사업)</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 220px;">
                        <label style="font-size: 0.85rem; color: #94a3b8; display: block; margin-bottom: 5px;">2. 주요 산업/비즈니스 모델 선택</label>
                        <select id="guide-industry-select" class="val-select">
                            <option value="aiApp">AI 애플리케이션 / 플랫폼 (Pre-revenue)</option>
                            <option value="deepTech">AI 반도체 / NPU 팹리스 / HW</option>
                            <option value="saas">Enterprise AI SW / B2B SaaS</option>
                            <option value="robotics">AI 로보틱스 / 물류 인프라</option>
                            <option value="biotech">바이오 / 표적항암 신약 파이프라인</option>
                            <option value="unicorn">복합 비즈니스 / Late-Stage 유니콘</option>
                        </select>
                    </div>
                </div>
                <div id="guide-recommendation-box" class="guide-rec-box">
                    <!-- Dynamic Recommendation Box -->
                </div>
            </div>

            <!-- 6대 밸류에이션 기법 총괄 매트릭스 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">📊 6대 밸류에이션 기법 총괄 비교 매트릭스</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>시트 / 기법</th>
                                <th>대상 산업군</th>
                                <th>적용 라운드</th>
                                <th>주요 입력 변수 (Inputs)</th>
                                <th>산출 결과 (Outputs)</th>
                                <th>실무 신뢰도 및 한계점</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong style="color: #60a5fa;">M1. Scorecard & Berkus</strong></td>
                                <td>초기 AI 앱 / Pre-revenue</td>
                                <td><span class="badge" style="background:#3b82f6;">Pre-Seed ~ Seed</span></td>
                                <td>창업팀, 시장기회, 특허/IP, 해자, 벤치마크</td>
                                <td>Pre-money 기업가치</td>
                                <td>초기 정성평가 표준 / 심사역 주관성 개입</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #34d399;">M2. VC Method</strong></td>
                                <td>AI 반도체 / HW / 딥테크</td>
                                <td><span class="badge" style="background:#10b981;">Series A ~ B</span></td>
                                <td>목표 IRR, 타깃 PER, 5년차 순이익, 후속희석률</td>
                                <td>Pre/Post 가치, 잔여지분율, 회수액</td>
                                <td>수익률 역산 명확 / Terminal 추정 민감도</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #fcd34d;">M3. Forward Multiples & R40</strong></td>
                                <td>Enterprise AI SW / B2B SaaS</td>
                                <td><span class="badge" style="background:#f59e0b;">Series B ~ Pre-IPO</span></td>
                                <td>Forward ARR, YoY 성장률, NRR, FCF 마진</td>
                                <td>Rule of 40 프리미엄 멀티플, 지분가치</td>
                                <td>시장 친화적 / 멀티플 디레이팅 시 하락 위험</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #a78bfa;">M4. First Chicago Method</strong></td>
                                <td>AI 로보틱스 / 물류 플랫폼</td>
                                <td><span class="badge" style="background:#8b5cf6;">Series B ~ C</span></td>
                                <td>Best/Base/Failure 시나리오 FCF, 발생확률, g</td>
                                <td>확률가중 기업가치 (Weighted EV)</td>
                                <td>상·하방 리스크 동시 반영 / 시나리오 주관성</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #f472b6;">M5. BioTech rNPV</strong></td>
                                <td>바이오 / 신약 파이프라인</td>
                                <td><span class="badge" style="background:#ec4899;">임상 1상 ~ 2상</span></td>
                                <td>임상단계별 성공률(POS), L/O Upfront, 마일스톤</td>
                                <td>파이프라인 rNPV, 최종 지분가치</td>
                                <td>글로벌 빅파마 표준 / 임상 실패 시 전액 상각</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #38bdf8;">M6. SOTP & Waterfall</strong></td>
                                <td>복합 유니콘 (SW+HW+SI)</td>
                                <td><span class="badge" style="background:#0284c7;">Pre-IPO / 유니콘</span></td>
                                <td>사업부별 지표·배수, 우선주 청산우선권 조건</td>
                                <td>SOTP 합산 EV, 주주별 회수액(MOIC)</td>
                                <td>지배구조·우선권 완전 모델링 / 복잡도 높음</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 라운드별 가이드 테이블 -->
            <div class="val-card glass-panel">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">🎯 스타트업 라이프사이클별 최적 밸류에이션 선택 가이드</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>투자 라운드</th>
                                <th>재무 상태 (Financials)</th>
                                <th>1순위 추천 기법</th>
                                <th>2순위 보조 기법</th>
                                <th>핵심 피칭 & 심사 포인트</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Pre-Seed / Seed</strong></td>
                                <td>매출 전 (Pre-revenue), 아이디어 및 MVP 단계</td>
                                <td><strong style="color:#60a5fa;">Scorecard / Berkus Method</strong></td>
                                <td>Cost-to-Duplicate (대체원가법)</td>
                                <td>창업팀/엔지니어 맨파워, 기술 독점성, 타깃 시장 규모</td>
                            </tr>
                            <tr>
                                <td><strong>Series A</strong></td>
                                <td>초기 매출 시현, PoC 완료, PMF(적합성) 검증</td>
                                <td><strong style="color:#34d399;">VC Method (역산 할인 모델)</strong></td>
                                <td>First Chicago Method</td>
                                <td>단위경제학(Unit Economics), 엑시트 시점 목표 PER 회수</td>
                            </tr>
                            <tr>
                                <td><strong>Series B ~ C</strong></td>
                                <td>고속 스케일업 (ARR 100억+), 해외 진출</td>
                                <td><strong style="color:#fcd34d;">Forward EV/ARR + Rule of 40</strong></td>
                                <td>rNPV (바이오), 시나리오 DCF</td>
                                <td>순매출유지율(NRR), Rule of 40 달성, 고객 락인(Moat)</td>
                            </tr>
                            <tr>
                                <td><strong>Pre-IPO / Unicorn</strong></td>
                                <td>BEP 달성 또는 대규모 FCF 창출, 사업 다각화</td>
                                <td><strong style="color:#38bdf8;">SOTP (부문별 합산) + Waterfall</strong></td>
                                <td>전통적 DCF, 상장비교 PER/EV-EBITDA</td>
                                <td>사업부별 밸류에이션, 우선주 청산우선권 및 엑시트 분배</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // Guide logic
        const roundSelect = document.getElementById('guide-round-select');
        const indSelect = document.getElementById('guide-industry-select');
        const recBox = document.getElementById('guide-recommendation-box');

        const updateRecommendation = () => {
            const r = roundSelect.value;
            const ind = indSelect.value;

            let recTitle = '';
            let recMethod = '';
            let recTab = '';
            let recDesc = '';
            let keyPoints = [];

            if (ind === 'biotech') {
                recTitle = '🧬 바이오 / 표적항암 신약 파이프라인 추천';
                recMethod = 'M5. rNPV (위험조정 순현재가치 타임라인 모델)';
                recTab = 'm5';
                recDesc = '바이오는 전통 재무지표보다 각 임상 단계(1상~3상, NDA)별 역사적 성공률(POS)과 글로벌 빅파마 대상 L/O 마일스톤 계약 현금흐름을 할인하는 rNPV가 전 세계 표준입니다.';
                keyPoints = ['임상 단계별 성공확률(POS) 누적 가중', '기술수출 Upfront + 마일스톤 + 상용화 로열티', 'Bridge to Equity: 플랫폼 가치 및 순현금 가산'];
            } else if (r === 'seed' || ind === 'aiApp') {
                recTitle = '📱 극초기 시드 AI 스타트업 추천';
                recMethod = 'M1. Scorecard & Berkus Method (초기 가중 평가법)';
                recTab = 'm1';
                recDesc = '매출이 발생하기 전(Pre-revenue) 단계에서는 재무적 추정치보다 창업팀 역량, 시장 잠재력, 핵심 특허, 5대 위험 감소 성공요소를 기반으로 프리머니 가치를 합리적으로 도출합니다.';
                keyPoints = ['동종업계 평균 벤치마크 30억 대비 7개 정성 요소 가중 조정', '베르쿠스 5대 위험감소 항목 각 7억 상한선 평가', '두 기법 평균값으로 최종 Term Sheet 밸류 합의'];
            } else if (r === 'seriesA' || ind === 'deepTech') {
                recTitle = '⚡ AI 팹리스 / 딥테크 하드웨어 추천';
                recMethod = 'M2. VC Method (목표 IRR 기반 역산 할인 모델)';
                recTab = 'm2';
                recDesc = '시리즈 A 투자 단계에서 투자자의 목표 회수 수익률(Target IRR)과 Exit 시점의 목표 PER, 그리고 후속 라운드 희석률을 종합 반영하여 적정 Pre/Post-money를 역산합니다.';
                keyPoints = ['5년차 순이익 × 목표 PER 25배 = Terminal Value', '목표 IRR 30% 기준 3.71배 회수 목표', '2차원 민감도 분석 (IRR vs 희석률)으로 적정 가치 밴드 확정'];
            } else if (r === 'seriesB' || ind === 'saas') {
                recTitle = '🚀 Enterprise AI SW & B2B SaaS 추천';
                recMethod = 'M3. Forward EV/ARR Multiples & Rule of 40';
                recTab = 'm3';
                recDesc = 'ARR 100억 이상 고성장 SaaS 기업은 차년도 선도 매출(Forward ARR)에 Rule of 40 초과 프리미엄 및 순매출유지율(NRR) 초과 프리미엄을 반영한 멀티플을 적용합니다.';
                keyPoints = ['성장률 + FCF마진 = Rule of 40 점수 산출', 'NRR 130% 초과 우량 고객 락인 멀티플 할증', '2차원 민감도 분석 (ARR vs Multiples) 실시간 연동'];
            } else if (ind === 'robotics') {
                recTitle = '🎯 AI 로보틱스 / 물류 플랫폼 추천';
                recMethod = 'M4. First Chicago Method (3대 시나리오 DCF)';
                recTab = 'm4';
                recDesc = '고성장 성공(Best), 현실적 기본(Base), 피벗 실패(Failure) 3대 시나리오의 5개년 FCF를 각각 DCF 모델링한 후, 발생 확률로 가중평균하여 균형 잡힌 기업가치를 산출합니다.';
                keyPoints = ['Best(20%), Base(55%), Failure(25%) 시나리오 구성', '영구성장률(g) 및 WACC 할인율 시나리오별 차등 적용', '하방 위험(Downside)과 업사이드 포텐셜 동시 반영'];
            } else {
                recTitle = '🦄 복합 유니콘 & 후기 라운드 추천';
                recMethod = 'M6. SOTP (부문별 합산) & 우선주 청산 워터폴';
                recTab = 'm6';
                recDesc = 'GenAI SW, 하드웨어, IT 서비스 등 여러 사업부를 개별 평가 배수로 합산(SOTP)하고, 우선주 주주별 청산우선권(참가적/비참가적) 워터폴을 모델링하여 실제 회수금을 산출합니다.';
                keyPoints = ['사업부문별 Forward ARR, PER, EBITDA 최적 배수 합산', 'Series C 비참가적 우선주의 보통주 전환 분기점 시뮬레이션', 'Exit 매각가 변동에 따른 주주별 최종 투자배수(MOIC) 도출'];
            }

            recBox.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 15px; flex-wrap: wrap;">
                    <div>
                        <h4 style="color: #38bdf8; font-size: 1.1rem; margin-bottom: 5px;">${recTitle}</h4>
                        <div style="font-size: 1.2rem; font-weight: bold; color: #f8fafc; margin-bottom: 8px;">
                            추천 1순위: <span style="color: #facc15;">${recMethod}</span>
                        </div>
                        <p style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.5; margin-bottom: 10px;">${recDesc}</p>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            ${keyPoints.map(p => `<span class="val-chip">✓ ${p}</span>`).join('')}
                        </div>
                    </div>
                    <button type="button" class="btn-primary" onclick="document.querySelector('.val-tab-btn[data-tab=\\'${recTab}\\']').click();" style="white-space: nowrap; padding: 10px 16px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);">
                        해당 모델 계산기로 이동 ➔
                    </button>
                </div>
            `;
        };

        roundSelect.addEventListener('change', updateRecommendation);
        indSelect.addEventListener('change', updateRecommendation);
        updateRecommendation();
    };

    // -------------------------------------------------------------
    // Tab 2: M1. Scorecard & Berkus Method
    // -------------------------------------------------------------
    const renderM1 = (container) => {
        const data = ValuationEngine.calculateM1();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>📱 2. M1: Scorecard & Berkus Method (초기 시드 AI 앱 스타트업)</h2>
                    <p class="subtitle">매출 발생 전(Pre-revenue) 초기 단계 기업의 정성적 역량을 벤치마크 및 5대 핵심 요소로 정량화</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel">
                    <span class="label">동종업계 기준 밸류 (Baseline)</span>
                    <span class="val" style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.baseline)}</span>
                    <span class="sub">지역/산업 평균 프리머니</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">Scorecard법 Pre-money</span>
                    <span class="val" style="color: #34d399;">${ValuationEngine.formatCurrency(data.scorecardPreMoney)}</span>
                    <span class="sub">가중 배수: ${(data.totalScorecardMultiplier * 100).toFixed(1)}%</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">Berkus법 Pre-money</span>
                    <span class="val" style="color: #fcd34d;">${ValuationEngine.formatCurrency(data.totalBerkusPreMoney)}</span>
                    <span class="sub">5대 위험감소 최대 35억 중 인정액</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #8b5cf6;">
                    <span class="label">두 기법 평균 Pre-money</span>
                    <span class="val" style="color: #c084fc;">${ValuationEngine.formatCurrency(data.combinedAveragePreMoney)}</span>
                    <span class="sub">최종 투자심의 권고 밸류</span>
                </div>
            </div>

            <!-- 파라미터 컨트롤: 베이스라인 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap;">
                <div>
                    <strong style="font-size: 1rem; color: #f8fafc;">동종 업계/지역 평균 프리머니 가치 (Baseline Pre-money Valuation)</strong>
                    <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 3px;">국내외 초기 AI 앱 스타트업의 최근 시드 투자 평균 밸류에이션</p>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <input type="range" id="m1-baseline-slider" min="10" max="100" step="5" value="${data.baseline}" style="width: 150px;">
                    <input type="number" id="m1-baseline-input" class="val-input-num" value="${data.baseline}" min="5" max="200" step="1">
                    <span style="color: #cbd5e1;">억 원</span>
                </div>
            </div>

            <!-- 1. Scorecard Method Table -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">1. Scorecard Method (스코어카드 평가법: 7대 평가 요소 가중 조정)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>평가 요소 (Criteria)</th>
                                <th>표준 가중치</th>
                                <th>상대 점수 (Score)</th>
                                <th>가중 배수</th>
                                <th>가치 기여액</th>
                                <th>평가 근거 및 실무 실사(Due Diligence) 기준</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.scorecardRows.map(row => `
                                <tr>
                                    <td><strong>${row.name}</strong></td>
                                    <td>${(row.weight * 100).toFixed(0)}%</td>
                                    <td style="min-width: 160px;">
                                        <div style="display: flex; align-items: center; gap: 8px;">
                                            <input type="range" class="m1-sc-slider" data-id="${row.id}" min="0.5" max="2.0" step="0.05" value="${row.score}" style="flex:1;">
                                            <span class="m1-sc-val" style="min-width: 35px; font-weight: bold; color: #60a5fa;">${row.score.toFixed(2)}</span>
                                        </div>
                                    </td>
                                    <td>${(row.mult * 100).toFixed(1)}%</td>
                                    <td style="font-weight: bold; color: #34d399;">${ValuationEngine.formatCurrency(row.contrib)}</td>
                                    <td style="font-size: 0.85rem; color: #94a3b8;">${row.reason}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(255,255,255,0.05); font-weight: bold;">
                                <td>합계 (Total Weighted Score)</td>
                                <td>100%</td>
                                <td>-</td>
                                <td style="color: #60a5fa;">${(data.totalScorecardMultiplier * 100).toFixed(1)}%</td>
                                <td style="color: #34d399; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.scorecardPreMoney)}</td>
                                <td>최종 스코어카드 산정 Pre-money 기업가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- 2. Berkus Method Table -->
            <div class="val-card glass-panel">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">2. Berkus Method (베르쿠스 평가법: 5대 핵심 위험감소 요소 상한선 합산)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>성공 위험감소 요소 (Risk-Reduction Element)</th>
                                <th>최대 인정 가치 (Max Cap)</th>
                                <th>인정 비율 (Achieved %)</th>
                                <th>산출 가치</th>
                                <th>달성 상세 내역 및 실사 확인 사항</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.berkusRows.map(row => `
                                <tr>
                                    <td><strong>${row.name}</strong></td>
                                    <td>${ValuationEngine.formatCurrency(row.maxCap)}</td>
                                    <td style="min-width: 180px;">
                                        <div style="display: flex; align-items: center; gap: 8px;">
                                            <input type="range" class="m1-bk-slider" data-id="${row.id}" min="0" max="1.0" step="0.05" value="${row.achieved}" style="flex:1;">
                                            <span class="m1-bk-val" style="min-width: 40px; font-weight: bold; color: #fcd34d;">${(row.achieved * 100).toFixed(0)}%</span>
                                        </div>
                                    </td>
                                    <td style="font-weight: bold; color: #34d399;">${ValuationEngine.formatCurrency(row.val)}</td>
                                    <td style="font-size: 0.85rem; color: #94a3b8;">${row.note}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(255,255,255,0.05); font-weight: bold;">
                                <td>베르쿠스법 최종 합산 가치</td>
                                <td>${ValuationEngine.formatCurrency(data.totalBerkusMax)}</td>
                                <td>-</td>
                                <td style="color: #fcd34d; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.totalBerkusPreMoney)}</td>
                                <td>Pre-revenue 초기 상한선 합산 가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

        // Event Bindings
        const state = ValuationEngine.getState();
        const baseSlider = document.getElementById('m1-baseline-slider');
        const baseInput = document.getElementById('m1-baseline-input');

        const updateBaseline = (val) => {
            state.m1.baseline = Number(val);
            renderM1(container);
        };
        baseSlider.addEventListener('input', (e) => updateBaseline(e.target.value));
        baseInput.addEventListener('change', (e) => updateBaseline(e.target.value));

        // Scorecard sliders
        container.querySelectorAll('.m1-sc-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const id = e.target.dataset.id;
                const item = state.m1.scorecard.find(x => x.id === id);
                if (item) {
                    item.score = Number(e.target.value);
                    renderM1(container);
                }
            });
        });

        // Berkus sliders
        container.querySelectorAll('.m1-bk-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const id = e.target.dataset.id;
                const item = state.m1.berkus.find(x => x.id === id);
                if (item) {
                    item.achieved = Number(e.target.value);
                    renderM1(container);
                }
            });
        });
    };

    // -------------------------------------------------------------
    // Tab 3: M2. VC Method (DeepTech)
    // -------------------------------------------------------------
    const renderM2 = (container) => {
        const data = ValuationEngine.calculateM2();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>⚡ 3. M2: VC Method 역산 할인 모델 (AI 팹리스 / 딥테크 HW)</h2>
                    <p class="subtitle">목표 투자수익률(IRR), Exit 시점 PER, 후속 지분희석을 반영한 시리즈 A 역산 밸류에이션 및 2차원 민감도 분석</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel">
                    <span class="label">예상 Exit 기업가치 (Terminal Value)</span>
                    <span class="val" style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.terminalValue)}</span>
                    <span class="sub">5년차 순이익(150억) × PER(25배)</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">목표 회수 배수 (Target Multiple)</span>
                    <span class="val" style="color: #fcd34d;">${data.targetMultiple.toFixed(2)}배</span>
                    <span class="sub">(1 + IRR 30%)^5년</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">적정 Post-money 가치</span>
                    <span class="val" style="color: #34d399;">${ValuationEngine.formatCurrency(data.postMoney)}</span>
                    <span class="sub">희석감안 TV(2,250억) ÷ 3.71배</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #3b82f6;">
                    <span class="label">금번 라운드 Pre-money 가치</span>
                    <span class="val" style="color: #38bdf8;">${ValuationEngine.formatCurrency(data.preMoney)}</span>
                    <span class="sub">투자금 100억 차감 후</span>
                </div>
            </div>

            <!-- 1. 핵심 파라미터 입력단 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">1. 투자 기본 조건 및 Exit 시점 추정치 (Inputs)</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                    
                    <div class="val-input-group">
                        <div class="label-row">
                            <span>금번 투자 유치액 (Investment)</span>
                            <span class="val-pill" id="m2-inv-val">${data.investment} 억원</span>
                        </div>
                        <input type="range" id="m2-inv-slider" min="10" max="300" step="5" value="${data.investment}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>투자 회수 기간 (Holding Period, t)</span>
                            <span class="val-pill" id="m2-years-val">${data.holdingYears} 년</span>
                        </div>
                        <input type="range" id="m2-years-slider" min="3" max="10" step="1" value="${data.holdingYears}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>투자자 목표 내부수익률 (Target IRR)</span>
                            <span class="val-pill" id="m2-irr-val">${(data.targetIRR * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m2-irr-slider" min="0.10" max="0.50" step="0.01" value="${data.targetIRR}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>5년 차 예상 당기순이익 (Exit Net Income)</span>
                            <span class="val-pill" id="m2-ni-val">${data.exitNetIncome} 억원</span>
                        </div>
                        <input type="range" id="m2-ni-slider" min="30" max="500" step="10" value="${data.exitNetIncome}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>Exit 시점 타깃 PER 배수 (Target PER)</span>
                            <span class="val-pill" id="m2-per-val">${data.targetPER} 배</span>
                        </div>
                        <input type="range" id="m2-per-slider" min="10" max="50" step="1" value="${data.targetPER}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>후속 라운드 누적 지분희석률 (Dilution)</span>
                            <span class="val-pill" id="m2-dil-val">${(data.dilution * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m2-dil-slider" min="0.10" max="0.70" step="0.05" value="${data.dilution}">
                    </div>

                </div>
            </div>

            <!-- 2. Step-by-Step 수식 연동 단계별 테이블 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">2. 밸류에이션 역산 및 지분 배분 계산 단계 (Step-by-Step Calculations)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>계산 단계</th>
                                <th>산출 공식 (Excel Formula)</th>
                                <th>수식 연동 결과</th>
                                <th>단위</th>
                                <th>결과 해석 및 투자자 의미</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>1. 예상 Exit 기업가치 (Terminal Value)</td>
                                <td><code>5년차 당기순이익 × 목표 PER</code></td>
                                <td style="font-weight: bold; color: #60a5fa;">${ValuationEngine.formatNumber(data.terminalValue)}</td>
                                <td>억원</td>
                                <td>5년 후 상장/M&A 시점 총 기업가치</td>
                            </tr>
                            <tr>
                                <td>2. 목표 회수 배수 (Target Multiple)</td>
                                <td><code>(1 + Target IRR) ^ t</code></td>
                                <td style="font-weight: bold; color: #fcd34d;">${data.targetMultiple.toFixed(3)}</td>
                                <td>배 (x)</td>
                                <td>5년간 원금 대비 필요 회수 배수</td>
                            </tr>
                            <tr>
                                <td>3. 희석 감안 유효 회수 가치 (Diluted TV)</td>
                                <td><code>Terminal Value × (1 - Dilution)</code></td>
                                <td style="font-weight: bold; color: #34d399;">${ValuationEngine.formatNumber(data.dilutedTV)}</td>
                                <td>억원</td>
                                <td>후속 라운드 희석 후 금번 투자자 지분 풀</td>
                            </tr>
                            <tr style="background: rgba(59, 130, 246, 0.1);">
                                <td><strong>4. 투자 후 기업가치 (Post-money Value)</strong></td>
                                <td><code>Diluted TV ÷ Target Multiple</code></td>
                                <td style="font-weight: bold; color: #38bdf8; font-size: 1.05rem;">${ValuationEngine.formatNumber(data.postMoney)}</td>
                                <td>억원</td>
                                <td>투자 직후 인정되는 적정 기업가치</td>
                            </tr>
                            <tr style="background: rgba(16, 185, 129, 0.1);">
                                <td><strong>5. 투자 전 기업가치 (Pre-money Value)</strong></td>
                                <td><code>Post-money Value - 투자 유치액</code></td>
                                <td style="font-weight: bold; color: #10b981; font-size: 1.05rem;">${ValuationEngine.formatNumber(data.preMoney)}</td>
                                <td>억원</td>
                                <td>금번 텀시트(Term Sheet) 상의 Pre-money Value</td>
                            </tr>
                            <tr>
                                <td>6. 금번 투자자 취득 지분율</td>
                                <td><code>금번 투자금 ÷ Post-money Value</code></td>
                                <td style="font-weight: bold;">${(data.acquiredShare * 100).toFixed(2)}%</td>
                                <td>%</td>
                                <td>시리즈 A 납입 직후 투자자 지분율</td>
                            </tr>
                            <tr>
                                <td>7. Exit 시점 잔여 지분율</td>
                                <td><code>초기 지분율 × (1 - Dilution)</code></td>
                                <td style="font-weight: bold;">${(data.exitShare * 100).toFixed(2)}%</td>
                                <td>%</td>
                                <td>후속 희석 감안 최종 엑시트 지분율</td>
                            </tr>
                            <tr>
                                <td>8. 예상 회수 금액 (Exit Cash Flow)</td>
                                <td><code>Terminal Value × 잔여 지분율</code></td>
                                <td style="font-weight: bold; color: #f59e0b;">${ValuationEngine.formatNumber(data.exitCashFlow)}</td>
                                <td>억원</td>
                                <td>원금 ${data.investment}억 × ${data.targetMultiple.toFixed(2)}배 회수 달성</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 3. 2차원 민감도 분석 매트릭스 -->
            <div class="val-card glass-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="color: #f8fafc; margin: 0;">📊 3. 2차원 민감도 매트릭스: 목표 IRR vs 후속 희석률 (Pre-money 가치, 단위: 억원)</h3>
                        <p style="font-size: 0.85rem; color: #94a3b8; margin-top: 3px;">현재 설정된 파라미터의 위치는 녹색 테두리로 실시간 하이라이트됩니다.</p>
                    </div>
                    <span class="val-chip" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981;">
                        현재 선택: IRR ${(data.targetIRR*100).toFixed(0)}% / 희석률 ${(data.dilution*100).toFixed(0)}% → ${ValuationEngine.formatCurrency(data.preMoney)}
                    </span>
                </div>
                <div class="table-container">
                    <table class="val-table val-matrix-table">
                        <thead>
                            <tr>
                                <th style="background: rgba(0,0,0,0.4);">후속 희석률 \\ 목표 IRR</th>
                                ${data.irrRange.map(irr => `
                                    <th style="${Math.abs(irr - data.targetIRR) < 0.001 ? 'background: rgba(59, 130, 246, 0.3); color: #60a5fa;' : ''}">
                                        IRR ${(irr * 100).toFixed(0)}%
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.sensitivityMatrix.map(row => `
                                <tr>
                                    <th style="background: rgba(0,0,0,0.3); ${Math.abs(row.dilution - data.dilution) < 0.001 ? 'background: rgba(59, 130, 246, 0.3); color: #60a5fa;' : ''}">
                                        희석률 ${(row.dilution * 100).toFixed(0)}%
                                    </th>
                                    ${row.values.map(cell => `
                                        <td class="${cell.isActive ? 'matrix-active-cell' : ''}" style="${cell.preMoney < 0 ? 'color: #ef4444;' : ''}">
                                            ${ValuationEngine.formatNumber(cell.preMoney)}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // Interactive bindings
        const state = ValuationEngine.getState();
        const bindSlider = (id, key, isPercent = false) => {
            const slider = document.getElementById(id);
            if (!slider) return;
            slider.addEventListener('input', (e) => {
                state.m2[key] = Number(e.target.value);
                renderM2(container);
            });
        };

        bindSlider('m2-inv-slider', 'investment');
        bindSlider('m2-years-slider', 'holdingYears');
        bindSlider('m2-irr-slider', 'targetIRR', true);
        bindSlider('m2-ni-slider', 'exitNetIncome');
        bindSlider('m2-per-slider', 'targetPER');
        bindSlider('m2-dil-slider', 'dilution', true);
    };

    // -------------------------------------------------------------
    // Tab 4: M3. Forward Multiples & Rule of 40 (SaaS)
    // -------------------------------------------------------------
    const renderM3 = (container) => {
        const data = ValuationEngine.calculateM3();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>🚀 4. M3: Forward EV/ARR Multiples & Rule of 40 (Enterprise AI SaaS)</h2>
                    <p class="subtitle">선도 매출 배수에 순매출유지율(NRR) 및 Rule of 40 프리미엄을 가산한 스케일업 지분가치 모델</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel">
                    <span class="label">Rule of 40 스코어</span>
                    <span class="val" style="color: ${data.r40Score >= 0.40 ? '#34d399' : '#f87171'};">${(data.r40Score * 100).toFixed(1)}%</span>
                    <span class="sub">성장률 ${(data.yoyGrowth * 100).toFixed(1)}% + FCF ${(data.fcfMargin * 100).toFixed(1)}%</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">최종 적용 Forward ARR 배수</span>
                    <span class="val" style="color: #fcd34d;">${data.finalMultiple.toFixed(2)}배</span>
                    <span class="sub">기본 8.5x + R40 ${data.r40Premium.toFixed(2)}x + NRR ${data.nrrPremium.toFixed(2)}x</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">기업 총 가치 (Enterprise Value)</span>
                    <span class="val" style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.enterpriseValue)}</span>
                    <span class="sub">차년도 ARR ${data.forwardARR}억 × ${data.finalMultiple.toFixed(2)}배</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #10b981;">
                    <span class="label">최종 지분가치 (Equity Value)</span>
                    <span class="val" style="color: #34d399;">${ValuationEngine.formatCurrency(data.equityValue)}</span>
                    <span class="sub">순현금 ${Math.abs(data.netDebt)}억원 가산</span>
                </div>
            </div>

            <!-- 파라미터 입력단 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">1. AI SaaS 기업 핵심 지표 및 프리미엄 승수 (Inputs)</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                    
                    <div class="val-input-group">
                        <div class="label-row">
                            <span>현재 연간 반복 매출 (Current ARR)</span>
                            <span class="val-pill">${data.currentARR} 억원</span>
                        </div>
                        <input type="range" id="m3-curr-arr-slider" min="30" max="300" step="10" value="${data.currentARR}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>차년도 예상 ARR (Forward 1Y ARR)</span>
                            <span class="val-pill">${data.forwardARR} 억원</span>
                        </div>
                        <input type="range" id="m3-fwd-arr-slider" min="50" max="600" step="10" value="${data.forwardARR}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>순매출 유지율 (NRR)</span>
                            <span class="val-pill">${(data.nrr * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m3-nrr-slider" min="0.90" max="1.60" step="0.01" value="${data.nrr}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>잉여현금흐름 마진율 (FCF Margin)</span>
                            <span class="val-pill">${(data.fcfMargin * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m3-fcf-slider" min="-0.50" max="0.30" step="0.01" value="${data.fcfMargin}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>상장 Peer 평균 EV/ARR 배수</span>
                            <span class="val-pill">${data.peerMultiple} 배</span>
                        </div>
                        <input type="range" id="m3-peer-slider" min="4.0" max="20.0" step="0.5" value="${data.peerMultiple}">
                    </div>

                    <div class="val-input-group">
                        <div class="label-row">
                            <span>보유 순차입금 (Net Debt, 음수는 순현금)</span>
                            <span class="val-pill">${data.netDebt} 억원</span>
                        </div>
                        <input type="range" id="m3-debt-slider" min="-200" max="100" step="10" value="${data.netDebt}">
                    </div>

                </div>
            </div>

            <!-- Step by step 테이블 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">2. 프리미엄 배수 및 최종 지분가치 산출 로직 (Calculations)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>산출 항목</th>
                                <th>계산 수식 (Excel Formula)</th>
                                <th>산출 결과</th>
                                <th>단위</th>
                                <th>투자자 관점 및 핵심 해석</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>예상 YoY 매출 성장률</td>
                                <td><code>(Forward ARR ÷ Current ARR) - 1</code></td>
                                <td style="font-weight: bold; color: #60a5fa;">${(data.yoyGrowth * 100).toFixed(1)}%</td>
                                <td>%</td>
                                <td>전년 대비 폭발적 성장률 견인</td>
                            </tr>
                            <tr>
                                <td>1. Rule of 40 스코어</td>
                                <td><code>매출 성장률 + FCF 마진율</code></td>
                                <td style="font-weight: bold; color: #fcd34d;">${(data.r40Score * 100).toFixed(1)}%</td>
                                <td>%</td>
                                <td>40% 기준 대비 압도적 초과 달성</td>
                            </tr>
                            <tr>
                                <td>2. Rule of 40 초과 프리미엄 배수</td>
                                <td><code>MAX(0, (Score - 40%) * 100) × 0.08</code></td>
                                <td style="font-weight: bold; color: #34d399;">+${data.r40Premium.toFixed(2)}</td>
                                <td>배 (x)</td>
                                <td>초과 성장성과 단위경제성에 대한 멀티플 할증</td>
                            </tr>
                            <tr>
                                <td>3. NRR 초과 프리미엄 배수</td>
                                <td><code>MAX(0, (NRR - 100%) * 100) × 0.15</code></td>
                                <td style="font-weight: bold; color: #34d399;">+${data.nrrPremium.toFixed(2)}</td>
                                <td>배 (x)</td>
                                <td>고객 락인 및 높은 업셀링 능력에 대한 할증</td>
                            </tr>
                            <tr style="background: rgba(250, 204, 21, 0.1);">
                                <td><strong>4. 최종 적용 Forward ARR 배수</strong></td>
                                <td><code>기본 배수 + R40 프리미엄 + NRR 프리미엄</code></td>
                                <td style="font-weight: bold; color: #facc15; font-size: 1.05rem;">${data.finalMultiple.toFixed(2)}</td>
                                <td>배 (x)</td>
                                <td>성장성 및 건전성이 모두 반영된 타깃 배수</td>
                            </tr>
                            <tr>
                                <td>5. 기업가치 (Enterprise Value)</td>
                                <td><code>차년도 예상 ARR × 최종 멀티플</code></td>
                                <td style="font-weight: bold; color: #38bdf8;">${ValuationEngine.formatNumber(data.enterpriseValue)}</td>
                                <td>억원</td>
                                <td>영업자산 기준 기업 총 가치</td>
                            </tr>
                            <tr style="background: rgba(16, 185, 129, 0.1);">
                                <td><strong>6. 최종 지분가치 (Equity Value)</strong></td>
                                <td><code>Enterprise Value - 순차입금(Net Debt)</code></td>
                                <td style="font-weight: bold; color: #10b981; font-size: 1.05rem;">${ValuationEngine.formatNumber(data.equityValue)}</td>
                                <td>억원</td>
                                <td>순현금 ${Math.abs(data.netDebt)}억원 가산 후 최종 지분가치</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 2차원 민감도 분석 테이블 -->
            <div class="val-card glass-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="color: #f8fafc; margin: 0;">📊 3. 2차원 민감도 분석: Forward ARR Multiples vs 차년도 ARR 규모 (지분가치: 억원)</h3>
                        <p style="font-size: 0.85rem; color: #94a3b8; margin-top: 3px;">차년도 ARR 달성 수준과 멀티플 변동에 따른 최종 지분가치 시나리오</p>
                    </div>
                    <span class="val-chip" style="background: rgba(250, 204, 21, 0.2); color: #fcd34d; border: 1px solid #f59e0b;">
                        현재 지표: ARR ${data.forwardARR}억 / ${data.finalMultiple.toFixed(2)}x → ${ValuationEngine.formatCurrency(data.equityValue)}
                    </span>
                </div>
                <div class="table-container">
                    <table class="val-table val-matrix-table">
                        <thead>
                            <tr>
                                <th style="background: rgba(0,0,0,0.4);">멀티플 \\ 차년도 ARR</th>
                                ${data.arrRange.map(arr => `
                                    <th style="${Math.abs(arr - data.forwardARR) < 1 ? 'background: rgba(59, 130, 246, 0.3); color: #60a5fa;' : ''}">
                                        ${arr}억 ARR
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.sensitivityMatrix.map(row => `
                                <tr>
                                    <th style="background: rgba(0,0,0,0.3); ${Math.abs(row.multiple - data.finalMultiple) < 0.1 ? 'background: rgba(59, 130, 246, 0.3); color: #60a5fa;' : ''}">
                                        ${row.multiple.toFixed(1)}x
                                    </th>
                                    ${row.values.map(cell => `
                                        <td class="${cell.isActive ? 'matrix-active-cell' : ''}">
                                            ${ValuationEngine.formatNumber(cell.equityValue)}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // Interactive bindings
        const state = ValuationEngine.getState();
        const bindSlider = (id, key) => {
            const slider = document.getElementById(id);
            if (!slider) return;
            slider.addEventListener('input', (e) => {
                state.m3[key] = Number(e.target.value);
                renderM3(container);
            });
        };

        bindSlider('m3-curr-arr-slider', 'currentARR');
        bindSlider('m3-fwd-arr-slider', 'forwardARR');
        bindSlider('m3-nrr-slider', 'nrr');
        bindSlider('m3-fcf-slider', 'fcfMargin');
        bindSlider('m3-peer-slider', 'peerMultiple');
        bindSlider('m3-debt-slider', 'netDebt');
    };

    // -------------------------------------------------------------
    // Tab 5: M4. First Chicago Method (Robotics)
    // -------------------------------------------------------------
    const renderM4 = (container) => {
        const data = ValuationEngine.calculateM4();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>🎯 5. M4: First Chicago Method (AI 로보틱스 / 물류 플랫폼)</h2>
                    <p class="subtitle">최상(Best), 기본(Base), 실패(Failure) 시나리오별 5개년 FCF DCF와 발생 확률가중평균 기업가치</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel" style="border-color: #10b981;">
                    <span class="label">Best Case (최상, 20%)</span>
                    <span class="val" style="color: #34d399;">${ValuationEngine.formatCurrency(data.best.npv)}</span>
                    <span class="sub">가중 기댓값: ${ValuationEngine.formatCurrency(data.weightedBest)}</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #3b82f6;">
                    <span class="label">Base Case (기본, 55%)</span>
                    <span class="val" style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.base.npv)}</span>
                    <span class="sub">가중 기댓값: ${ValuationEngine.formatCurrency(data.weightedBase)}</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #ef4444;">
                    <span class="label">Failure Case (청산, 25%)</span>
                    <span class="val" style="color: #f87171;">${ValuationEngine.formatCurrency(data.failure.npv)}</span>
                    <span class="sub">가중 기댓값: ${ValuationEngine.formatCurrency(data.weightedFailure)}</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #f59e0b;">
                    <span class="label">최종 확률가중 기업가치 (EV)</span>
                    <span class="val" style="color: #fcd34d;">${ValuationEngine.formatCurrency(data.firstChicagoEV)}</span>
                    <span class="sub">하방 리스크 & 업사이드 통합</span>
                </div>
            </div>

            <!-- 시나리오 확률 조정 슬라이더 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">1. 시나리오별 발생 확률 조정 (합계 100%)</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem;">
                    <div>
                        <div class="label-row">
                            <span style="color: #34d399; font-weight: bold;">Best Case 확률</span>
                            <span class="val-pill">${(data.best.prob * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m4-best-prob" min="0.05" max="0.50" step="0.05" value="${data.best.prob}">
                    </div>
                    <div>
                        <div class="label-row">
                            <span style="color: #60a5fa; font-weight: bold;">Base Case 확률</span>
                            <span class="val-pill">${(data.base.prob * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m4-base-prob" min="0.20" max="0.80" step="0.05" value="${data.base.prob}">
                    </div>
                    <div>
                        <div class="label-row">
                            <span style="color: #f87171; font-weight: bold;">Failure Case 확률</span>
                            <span class="val-pill">${(data.failure.prob * 100).toFixed(0)} %</span>
                        </div>
                        <input type="range" id="m4-failure-prob" min="0.05" max="0.50" step="0.05" value="${data.failure.prob}">
                    </div>
                </div>
            </div>

            <!-- 시나리오별 5개년 FCF 예측 및 NPV 도출 테이블 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">2. 5개년 FCF 예측 및 시나리오별 현재가치(NPV) 도출 (단위: 억원)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>시나리오</th>
                                <th>Y1 FCF</th>
                                <th>Y2 FCF</th>
                                <th>Y3 FCF</th>
                                <th>Y4 FCF</th>
                                <th>Y5 FCF</th>
                                <th>영구성장률(g)</th>
                                <th>할인율(WACC)</th>
                                <th>Terminal Value</th>
                                <th>시나리오 기업가치 (NPV)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong style="color: #34d399;">Best Case</strong></td>
                                <td>${data.best.fcfs[0]}</td>
                                <td>${data.best.fcfs[1]}</td>
                                <td>${data.best.fcfs[2]}</td>
                                <td>${data.best.fcfs[3]}</td>
                                <td>${data.best.fcfs[4]}</td>
                                <td>${(data.best.g * 100).toFixed(1)}%</td>
                                <td>${(data.best.wacc * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #60a5fa;">${ValuationEngine.formatNumber(data.best.tv)}</td>
                                <td style="font-weight: bold; color: #34d399; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.best.npv)}</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #60a5fa;">Base Case</strong></td>
                                <td>${data.base.fcfs[0]}</td>
                                <td>${data.base.fcfs[1]}</td>
                                <td>${data.base.fcfs[2]}</td>
                                <td>${data.base.fcfs[3]}</td>
                                <td>${data.base.fcfs[4]}</td>
                                <td>${(data.base.g * 100).toFixed(1)}%</td>
                                <td>${(data.base.wacc * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #60a5fa;">${ValuationEngine.formatNumber(data.base.tv)}</td>
                                <td style="font-weight: bold; color: #60a5fa; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.base.npv)}</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #f87171;">Failure Case</strong></td>
                                <td>${data.failure.fcfs[0]}</td>
                                <td>${data.failure.fcfs[1]}</td>
                                <td>${data.failure.fcfs[2]}</td>
                                <td>${data.failure.fcfs[3]}</td>
                                <td>${data.failure.fcfs[4]}</td>
                                <td>0.0%</td>
                                <td>${(data.failure.wacc * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #94a3b8;">${data.failure.tv} (청산가치)</td>
                                <td style="font-weight: bold; color: #f87171; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.failure.npv)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 확률가중 종합 테이블 -->
            <div class="val-card glass-panel">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">3. First Chicago 확률가중 기업가치 종합 (Probability-Weighted Valuation)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>시나리오</th>
                                <th>시나리오별 기업가치 (NPV)</th>
                                <th>발생 확률</th>
                                <th>가중 기댓값 (Weighted Value)</th>
                                <th>비고 및 투자 시사점</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Best Case (최상)</td>
                                <td>${ValuationEngine.formatCurrency(data.best.npv)}</td>
                                <td>${(data.best.prob * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #34d399;">${ValuationEngine.formatCurrency(data.weightedBest)}</td>
                                <td>글로벌 물류사 독점 공급 성공 프리미엄 반영</td>
                            </tr>
                            <tr>
                                <td>Base Case (기본)</td>
                                <td>${ValuationEngine.formatCurrency(data.base.npv)}</td>
                                <td>${(data.base.prob * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #60a5fa;">${ValuationEngine.formatCurrency(data.weightedBase)}</td>
                                <td>현 사업계획 기준 가장 유력한 성장 경로</td>
                            </tr>
                            <tr>
                                <td>Failure Case (실패)</td>
                                <td>${ValuationEngine.formatCurrency(data.failure.npv)}</td>
                                <td>${(data.failure.prob * 100).toFixed(1)}%</td>
                                <td style="font-weight: bold; color: #f87171;">${ValuationEngine.formatCurrency(data.weightedFailure)}</td>
                                <td>경쟁 심화 및 피벗 실패 시 하방 리스크 감안</td>
                            </tr>
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(250, 204, 21, 0.1); font-weight: bold;">
                                <td>최종 확률가중 기업가치 (First Chicago EV)</td>
                                <td>-</td>
                                <td>${((data.best.prob + data.base.prob + data.failure.prob) * 100).toFixed(0)}%</td>
                                <td style="color: #facc15; font-size: 1.15rem;">${ValuationEngine.formatCurrency(data.firstChicagoEV)}</td>
                                <td>성공과 실패의 극단적 확률을 결합한 합리적 밸류에이션</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

        // Interactive bindings for probabilities
        const state = ValuationEngine.getState();
        const bindProb = (id, key) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', (e) => {
                state.m4[key].prob = Number(e.target.value);
                renderM4(container);
            });
        };

        bindProb('m4-best-prob', 'best');
        bindProb('m4-base-prob', 'base');
        bindProb('m4-failure-prob', 'failure');
    };

    // -------------------------------------------------------------
    // Tab 6: M5. BioTech rNPV Model
    // -------------------------------------------------------------
    const renderM5 = (container) => {
        const data = ValuationEngine.calculateM5();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>🧬 6. M5: rNPV 타임라인 모델 (바이오 / 표적항암 신약 파이프라인)</h2>
                    <p class="subtitle">임상 단계별 역사적 성공률(POS) 가중 및 글로벌 기술수출(L/O) 계약금·마일스톤·로열티 현금흐름 할인법</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel">
                    <span class="label">임상 최종 누적 성공확률</span>
                    <span class="val" style="color: #f472b6;">10.71%</span>
                    <span class="sub">1상(60%)→2상(35%)→3상(60%)→NDA(85%)</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">핵심 파이프라인 rNPV 합계</span>
                    <span class="val" style="color: #38bdf8;">${ValuationEngine.formatCurrency(data.totalPipelineRNPV)}</span>
                    <span class="sub">WACC ${(data.wacc * 100).toFixed(0)}% 할인 현금흐름 합산</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">비영업 가치 (플랫폼+순현금)</span>
                    <span class="val" style="color: #34d399;">${ValuationEngine.formatCurrency(data.bridgePlatform + data.bridgeCash + data.bridgeDebt)}</span>
                    <span class="sub">플랫폼 150억 + 현금 120억 - 부채 20억</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #ec4899;">
                    <span class="label">최종 Pre-money 지분가치</span>
                    <span class="val" style="color: #f472b6;">${ValuationEngine.formatCurrency(data.finalEquityValue)}</span>
                    <span class="sub">Bridge to Equity Value 합산</span>
                </div>
            </div>

            <!-- 10개년 타임라인 rNPV 테이블 -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="color: #f8fafc; margin: 0;">1. 10개년 연도별 위험조정 순현재가치(rNPV) 산출 타임라인 (단위: 억원)</h3>
                        <p style="font-size: 0.85rem; color: #94a3b8; margin-top: 3px;">할인율(WACC): ${(data.wacc * 100).toFixed(0)}% 적용</p>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 0.85rem; color: #cbd5e1;">할인율(WACC) 조정:</span>
                        <input type="range" id="m5-wacc-slider" min="0.10" max="0.30" step="0.01" value="${data.wacc}" style="width: 120px;">
                        <span class="val-pill">${(data.wacc * 100).toFixed(0)}%</span>
                    </div>
                </div>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>연도 (Year)</th>
                                <th>임상 단계 / 주요 마일스톤 이벤트</th>
                                <th>명목 현금흐름</th>
                                <th>임상 누적 성공확률 (POS)</th>
                                <th>위험조정 현금흐름</th>
                                <th>할인계수 (18%)</th>
                                <th>할인 rNPV</th>
                                <th>누적 rNPV</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.timeline.map(row => `
                                <tr>
                                    <td><strong>Y${row.year}</strong></td>
                                    <td>${row.event}</td>
                                    <td style="${row.nominalCF < 0 ? 'color: #f87171;' : 'color: #34d399;'} font-weight: bold;">
                                        ${row.nominalCF > 0 ? '+' : ''}${row.nominalCF}
                                    </td>
                                    <td>${(row.pos * 100).toFixed(2)}%</td>
                                    <td style="font-weight: bold;">${ValuationEngine.formatNumber(row.riskAdjCF)}</td>
                                    <td style="color: #94a3b8;">${row.discountFactor.toFixed(4)}</td>
                                    <td style="${row.discountedRNPV < 0 ? 'color: #f87171;' : 'color: #38bdf8;'} font-weight: bold;">
                                        ${ValuationEngine.formatNumber(row.discountedRNPV)}
                                    </td>
                                    <td style="font-weight: bold; color: #fcd34d;">${ValuationEngine.formatNumber(row.cumRNPV)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(255,255,255,0.05); font-weight: bold;">
                                <td colspan="2">합계 (Total Pipeline Valuation)</td>
                                <td style="color: #34d399;">${ValuationEngine.formatCurrency(data.totalNominalCF)}</td>
                                <td>-</td>
                                <td style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.totalRiskAdjCF)}</td>
                                <td>-</td>
                                <td style="color: #38bdf8; font-size: 1.05rem;">${ValuationEngine.formatCurrency(data.totalPipelineRNPV)}</td>
                                <td>핵심 파이프라인 순가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- Bridge to Equity Value 요약 -->
            <div class="val-card glass-panel">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">2. 최종 지분가치 환산 요약 (Bridge to Equity Value)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>평가 구성 항목</th>
                                <th>금액 (억원)</th>
                                <th>비고 및 산출 내역</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>1. 핵심 파이프라인 rNPV 가치</td>
                                <td style="font-weight: bold; color: #38bdf8;">${ValuationEngine.formatCurrency(data.totalPipelineRNPV)}</td>
                                <td>10개년 위험조정 순현재가치 합계</td>
                            </tr>
                            <tr>
                                <td>2. 플랫폼 기술 및 백업 파이프라인 가치</td>
                                <td style="font-weight: bold; color: #34d399;">+${data.bridgePlatform} 억원</td>
                                <td>독자적 AI 신약 발굴 플랫폼 프리미엄 가산</td>
                            </tr>
                            <tr>
                                <td>3. 보유 현금 및 금융자산 (Cash)</td>
                                <td style="font-weight: bold; color: #34d399;">+${data.bridgeCash} 억원</td>
                                <td>비영업용 유동성 자산 가산</td>
                            </tr>
                            <tr>
                                <td>4. 총 차입금 및 부채 (Total Debt)</td>
                                <td style="font-weight: bold; color: #f87171;">${data.bridgeDebt} 억원</td>
                                <td>단기차입금 및 전환사채 차감</td>
                            </tr>
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(236, 72, 153, 0.15); font-weight: bold;">
                                <td>최종 Pre-money 지분가치 (Equity Value)</td>
                                <td style="color: #f472b6; font-size: 1.15rem;">${ValuationEngine.formatCurrency(data.finalEquityValue)}</td>
                                <td>신규 투자유치(Series B) 시 공식 인정 기업가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

        // Interactive bindings
        const state = ValuationEngine.getState();
        const waccSlider = document.getElementById('m5-wacc-slider');
        if (waccSlider) {
            waccSlider.addEventListener('input', (e) => {
                state.m5.wacc = Number(e.target.value);
                renderM5(container);
            });
        }
    };

    // -------------------------------------------------------------
    // Tab 7: M6. Unicorn Late Stage (SOTP & Waterfall)
    // -------------------------------------------------------------
    const renderM6 = (container) => {
        const data = ValuationEngine.calculateM6();

        container.innerHTML = `
            <div class="val-section-header">
                <div>
                    <h2>🦄 7. M6: 유니콘 복합 가치평가 (SOTP & 청산우선권 워터폴)</h2>
                    <p class="subtitle">AI SW+HW 다각화 유니콘의 사업부문별 합산(SOTP) 및 엑시트 시 우선주 청산우선권(Waterfall) 시뮬레이션</p>
                </div>
            </div>

            <!-- 상단 요약 KPI 카드 -->
            <div class="val-kpi-grid">
                <div class="val-kpi-card glass-panel">
                    <span class="label">총 사업가치 합계 (SOTP EV)</span>
                    <span class="val" style="color: #38bdf8;">${ValuationEngine.formatCurrency(data.totalSOTPValue)}</span>
                    <span class="sub">SW + HW + SI + 부동산 합산</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">시뮬레이션 Exit 매각가</span>
                    <span class="val" style="color: #fcd34d;">${ValuationEngine.formatCurrency(data.exitValuation)}</span>
                    <span class="sub">청산우선권 배분 기준 금액</span>
                </div>
                <div class="val-kpi-card glass-panel">
                    <span class="label">Series C 우선주 상태</span>
                    <span class="val" style="color: ${data.seriesCConverts ? '#34d399' : '#f59e0b'};">
                        ${data.seriesCConverts ? '보통주 전환 (유리)' : '1x 우선권 행사'}
                    </span>
                    <span class="sub">전환가치 2,250억 vs 우선권 2,000억</span>
                </div>
                <div class="val-kpi-card glass-panel" style="border-color: #8b5cf6;">
                    <span class="label">보통주/창업자 최종 회수액</span>
                    <span class="val" style="color: #c084fc;">
                        ${ValuationEngine.formatCurrency(data.waterfallRows.find(r => r.id === 'common').totalPayout)}
                    </span>
                    <span class="sub">투자배수: ${data.waterfallRows.find(r => r.id === 'common').moic.toFixed(1)}배</span>
                </div>
            </div>

            <!-- 1. 사업부문별 합산 가치평가 (SOTP) -->
            <div class="val-card glass-panel" style="margin-bottom: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: #f8fafc;">1. 사업부문별 합산 가치평가 (Sum-of-the-Parts, SOTP)</h3>
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>사업 부문 (Division)</th>
                                <th>기준 실적 지표</th>
                                <th>실적 규모</th>
                                <th>적용 평가 배수</th>
                                <th>배수 기준</th>
                                <th>부문별 기업가치</th>
                                <th>적용 Peer 및 근거</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.sotpRows.map(row => `
                                <tr>
                                    <td><strong>${row.name}</strong></td>
                                    <td>${row.metricName}</td>
                                    <td>${row.value} 억원</td>
                                    <td style="font-weight: bold; color: #60a5fa;">${row.multiple} 배</td>
                                    <td><span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #93c5fd;">${row.base}</span></td>
                                    <td style="font-weight: bold; color: #34d399; font-size: 1.05rem;">${ValuationEngine.formatCurrency(row.ev)}</td>
                                    <td style="font-size: 0.85rem; color: #94a3b8;">${row.peer}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(59, 130, 246, 0.15); font-weight: bold;">
                                <td colspan="2">총 사업가치 합계 (SOTP Enterprise Value)</td>
                                <td>-</td>
                                <td>-</td>
                                <td>-</td>
                                <td style="color: #38bdf8; font-size: 1.15rem;">${ValuationEngine.formatCurrency(data.totalSOTPValue)}</td>
                                <td>유니콘 전체 합산 기업가치: 2조 2,000억 원</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- 2. 청산우선권 워터폴 시뮬레이션 -->
            <div class="val-card glass-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="color: #f8fafc; margin: 0;">2. Exit 시나리오별 청산우선권 배분 워터폴 (Liquidation Preference Waterfall)</h3>
                        <p style="font-size: 0.85rem; color: #94a3b8; margin-top: 3px;">엑시트 매각 총액(Exit Valuation) 변동에 따른 주주별 우선권 행사 및 잔여재산 안분 시뮬레이션</p>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 0.85rem; color: #cbd5e1;">Exit 매각가 조절:</span>
                        <input type="range" id="m6-exit-slider" min="2000" max="30000" step="500" value="${data.exitValuation}" style="width: 160px;">
                        <span class="val-pill" style="color: #fcd34d;">${ValuationEngine.formatCurrency(data.exitValuation)}</span>
                    </div>
                </div>

                <!-- 시각화 워터폴 누적 바 차트 -->
                <div style="margin-bottom: 1.5rem; background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;">
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 8px;">주주별 회수액 비중 시각화:</div>
                    <div class="waterfall-bar-container" style="display: flex; height: 32px; border-radius: 6px; overflow: hidden; background: #1e293b;">
                        ${data.waterfallRows.map((r, idx) => {
                            const pct = data.totalPayoutSum > 0 ? (r.totalPayout / data.totalPayoutSum) * 100 : 0;
                            const colors = ['#38bdf8', '#34d399', '#fcd34d', '#c084fc'];
                            return `
                                <div style="width: ${pct}%; background: ${colors[idx]}; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: bold; color: #0f172a; white-space: nowrap; overflow: hidden; padding: 0 4px;" title="${r.name}: ${ValuationEngine.formatCurrency(r.totalPayout)} (${pct.toFixed(1)}%)">
                                    ${pct >= 8 ? `${r.id.toUpperCase()} (${pct.toFixed(0)}%)` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <div style="display: flex; gap: 15px; margin-top: 8px; font-size: 0.8rem; color: #cbd5e1; flex-wrap: wrap;">
                        <span><span style="color: #38bdf8;">■</span> Series C (${((data.waterfallRows[0].totalPayout / data.totalPayoutSum) * 100).toFixed(1)}%)</span>
                        <span><span style="color: #34d399;">■</span> Series B (${((data.waterfallRows[1].totalPayout / data.totalPayoutSum) * 100).toFixed(1)}%)</span>
                        <span><span style="color: #fcd34d;">■</span> Series A (${((data.waterfallRows[2].totalPayout / data.totalPayoutSum) * 100).toFixed(1)}%)</span>
                        <span><span style="color: #c084fc;">■</span> 창업자/보통주 (${((data.waterfallRows[3].totalPayout / data.totalPayoutSum) * 100).toFixed(1)}%)</span>
                    </div>
                </div>

                <!-- 워터폴 테이블 -->
                <div class="table-container">
                    <table class="val-table">
                        <thead>
                            <tr>
                                <th>주주 구분 (Shareholder Class)</th>
                                <th>원금 투자액</th>
                                <th>청산우선권 조건</th>
                                <th>1단계: 우선권 회수</th>
                                <th>지분율</th>
                                <th>2단계: 잔여 보통주 배분</th>
                                <th>최종 총 회수 금액</th>
                                <th>투자 원금 대비 배수 (MOIC)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.waterfallRows.map(row => `
                                <tr>
                                    <td><strong>${row.name}</strong></td>
                                    <td>${ValuationEngine.formatCurrency(row.investment)}</td>
                                    <td>
                                        <span class="badge" style="${row.converted ? 'background:#10b981;' : 'background:#64748b;'}">
                                            ${row.converted ? '1x 비참가적 (보통주 전환)' : (row.prefType === 'participating' ? '1x 참가적 우선주' : '잔여 보통주')}
                                        </span>
                                    </td>
                                    <td style="font-weight: bold; color: #60a5fa;">${ValuationEngine.formatCurrency(row.step1Pref)}</td>
                                    <td>${(row.ownership * 100).toFixed(1)}%</td>
                                    <td style="font-weight: bold; color: #fcd34d;">${ValuationEngine.formatCurrency(row.step2Dist)}</td>
                                    <td style="font-weight: bold; color: #34d399; font-size: 1.05rem;">${ValuationEngine.formatCurrency(row.totalPayout)}</td>
                                    <td style="font-weight: bold; color: #a78bfa;">${row.moic.toFixed(2)}배</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: rgba(255,255,255,0.05); font-weight: bold;">
                                <td>합계 (Total Waterfall Payout)</td>
                                <td>${ValuationEngine.formatCurrency(data.waterfallRows.reduce((a, r) => a + r.investment, 0))}</td>
                                <td>-</td>
                                <td style="color: #60a5fa;">${ValuationEngine.formatCurrency(data.waterfallRows.reduce((a, r) => a + r.step1Pref, 0))}</td>
                                <td>100.0%</td>
                                <td style="color: #fcd34d;">${ValuationEngine.formatCurrency(data.waterfallRows.reduce((a, r) => a + r.step2Dist, 0))}</td>
                                <td style="color: #34d399; font-size: 1.15rem;">${ValuationEngine.formatCurrency(data.totalPayoutSum)}</td>
                                <td>${(data.totalPayoutSum / data.waterfallRows.reduce((a, r) => a + r.investment, 0)).toFixed(2)}배</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

        // Interactive bindings
        const state = ValuationEngine.getState();
        const exitSlider = document.getElementById('m6-exit-slider');
        if (exitSlider) {
            exitSlider.addEventListener('input', (e) => {
                state.m6.waterfall.exitValuation = Number(e.target.value);
                renderM6(container);
            });
        }
    };

    // -------------------------------------------------------------
    // Valuation Assessment Report Generation Engine (PDF & Word)
    // -------------------------------------------------------------
    const openReportModal = () => {
        const reportModal = document.getElementById('val-report-modal');
        const reportBody = document.getElementById('val-report-body');
        if (!reportModal || !reportBody) return;

        reportBody.innerHTML = generateValuationReportHTML();
        reportModal.style.display = 'flex';
    };

    const generateValuationReportHTML = () => {
        const today = new Date();
        const dateStr = `${today.getFullYear()}년 ${String(today.getMonth() + 1).padStart(2, '0')}월 ${String(today.getDate()).padStart(2, '0')}일`;
        
        let modelTitle = '';
        let targetRound = '';
        let execSummaryHtml = '';
        let detailSectionsHtml = '';
        let sensitivityHtml = '';
        let opinionHtml = '';

        if (currentTab === 'm1') {
            const d = ValuationEngine.calculateM1();
            modelTitle = 'M1. 스코어카드(Scorecard) & 베르쿠스(Berkus) 극초기 시드 가치평가';
            targetRound = 'Pre-Seed ~ Seed (매출 전 단계)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">동종업계 기준 밸류</span>
                        <span class="stat-val">${ValuationEngine.formatCurrency(d.baseline)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Scorecard 산정 가치</span>
                        <span class="stat-val" style="color: #2563eb;">${ValuationEngine.formatCurrency(d.scorecardPreMoney)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Berkus 산정 가치</span>
                        <span class="stat-val" style="color: #d97706;">${ValuationEngine.formatCurrency(d.totalBerkusPreMoney)}</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #7c3aed; background: #faf5ff;">
                        <span class="stat-label">최종 권고 Pre-money</span>
                        <span class="stat-val" style="color: #7c3aed;">${ValuationEngine.formatCurrency(d.combinedAveragePreMoney)}</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 스코어카드(Scorecard) 7대 항목 정성 평가 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>평가 항목</th>
                                <th>가중치</th>
                                <th>상대 점수</th>
                                <th>가중 배수</th>
                                <th>가치 기여액</th>
                                <th>실사 평가 근거</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.scorecardRows.map(r => `
                                <tr>
                                    <td><strong>${r.name}</strong></td>
                                    <td>${(r.weight * 100).toFixed(0)}%</td>
                                    <td>${r.score.toFixed(2)}</td>
                                    <td>${(r.mult * 100).toFixed(1)}%</td>
                                    <td style="font-weight: bold; color: #1e40af;">${ValuationEngine.formatCurrency(r.contrib)}</td>
                                    <td>${r.reason}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td>합계</td>
                                <td>100%</td>
                                <td>-</td>
                                <td>${(d.totalScorecardMultiplier * 100).toFixed(1)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.scorecardPreMoney)}</td>
                                <td>Scorecard 기준 Pre-money 가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div class="val-report-section">
                    <h3 class="val-report-section-title">2. 베르쿠스(Berkus) 5대 위험 감소 성공요소 평가 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>위험 감소 요소</th>
                                <th>최대 인정 한도 (Max Cap)</th>
                                <th>달성 인정률</th>
                                <th>산출 가치</th>
                                <th>실사 확인 사항</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.berkusRows.map(r => `
                                <tr>
                                    <td><strong>${r.name}</strong></td>
                                    <td>${ValuationEngine.formatCurrency(r.maxCap)}</td>
                                    <td>${(r.achieved * 100).toFixed(0)}%</td>
                                    <td style="font-weight: bold; color: #d97706;">${ValuationEngine.formatCurrency(r.val)}</td>
                                    <td>${r.note}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td>합계</td>
                                <td>${ValuationEngine.formatCurrency(d.totalBerkusMax)}</td>
                                <td>-</td>
                                <td>${ValuationEngine.formatCurrency(d.totalBerkusPreMoney)}</td>
                                <td>Berkus 기준 Pre-money 가치</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;

            opinionHtml = `
                매출 발생 전(Pre-revenue) 시드 단계임을 감안하여 정량적 재무지표 대신 창업팀의 탁월한 엔지니어링 역량과 핵심 IP 및 비공개 베타 트랙션을 높게 평가함.
                동종업계 기준 밸류(${ValuationEngine.formatCurrency(d.baseline)}) 대비 스코어카드 배수(${(d.totalScorecardMultiplier * 100).toFixed(1)}%)와 베르쿠스 5대 위험감소 가치(${ValuationEngine.formatCurrency(d.totalBerkusPreMoney)})의 산술평균인 <strong>${ValuationEngine.formatCurrency(d.combinedAveragePreMoney)}</strong>을 적정 Pre-money 가치로 제언함.
            `;
        } else if (currentTab === 'm3') {
            const d = ValuationEngine.calculateM3();
            modelTitle = 'M3. Forward EV/ARR Multiples & Rule of 40 (Enterprise SaaS)';
            targetRound = 'Series B ~ Pre-IPO (고속 스케일업 단계)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">차년도 선도 ARR (Forward)</span>
                        <span class="stat-val">${ValuationEngine.formatCurrency(d.forwardARR)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Rule of 40 점수</span>
                        <span class="stat-val" style="color: #059669;">${(d.r40Score * 100).toFixed(1)}%</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">최종 적용 EV/ARR 배수</span>
                        <span class="stat-val" style="color: #2563eb;">${d.finalMultiple.toFixed(2)}배</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #2563eb; background: #eff6ff;">
                        <span class="stat-label">적정 지분가치 (Equity Value)</span>
                        <span class="stat-val" style="color: #1e40af;">${ValuationEngine.formatCurrency(d.equityValue)}</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 멀티플 프리미엄 도출 및 가치 산출 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>평가 지표</th>
                                <th>실적치 / 산정치</th>
                                <th>기준 지표</th>
                                <th>초과분</th>
                                <th>멀티플 기여분</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Peer 그룹 기준 EV/ARR</strong></td>
                                <td>${d.peerMultiple.toFixed(1)}배</td>
                                <td>글로벌 SaaS 상장사 평균</td>
                                <td>-</td>
                                <td>+${d.peerMultiple.toFixed(2)}배</td>
                            </tr>
                            <tr>
                                <td><strong>Rule of 40 프리미엄</strong></td>
                                <td>${(d.r40Score * 100).toFixed(1)}% (성장률 ${(d.yoyGrowth * 100).toFixed(0)}% + FCF마진 ${(d.fcfMargin * 100).toFixed(0)}%)</td>
                                <td>40.0%</td>
                                <td>${Math.max(0, (d.r40Score - 0.40) * 100).toFixed(1)}%p</td>
                                <td>+${d.r40Premium.toFixed(2)}배</td>
                            </tr>
                            <tr>
                                <td><strong>순매출유지율(NRR) 프리미엄</strong></td>
                                <td>${(d.nrr * 100).toFixed(0)}%</td>
                                <td>100.0%</td>
                                <td>${Math.max(0, (d.nrr - 1.0) * 100).toFixed(1)}%p</td>
                                <td>+${d.nrrPremium.toFixed(2)}배</td>
                            </tr>
                            <tr class="total-row">
                                <td><strong>최종 산정 EV/ARR 멀티플</strong></td>
                                <td colspan="3">-</td>
                                <td><strong>${d.finalMultiple.toFixed(2)}배</strong></td>
                            </tr>
                            <tr>
                                <td><strong>기업가치 (Enterprise Value)</strong></td>
                                <td colspan="4">${ValuationEngine.formatCurrency(d.forwardARR)} × ${d.finalMultiple.toFixed(2)}배 = <strong>${ValuationEngine.formatCurrency(d.enterpriseValue)}</strong></td>
                            </tr>
                            <tr>
                                <td><strong>순차입금 (Net Debt) 차감</strong></td>
                                <td colspan="4">${ValuationEngine.formatCurrency(d.netDebt)} (순현금 상태)</td>
                            </tr>
                            <tr class="total-row" style="background:#eff6ff;">
                                <td><strong>최종 산정 지분가치 (Equity Value)</strong></td>
                                <td colspan="4" style="font-size: 1.1em; color: #1e3a8a;"><strong>${ValuationEngine.formatCurrency(d.equityValue)}</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;

            sensitivityHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">2. 2차원 민감도 분석 매트릭스 (Forward ARR vs EV/ARR 배수)</h3>
                    <p style="font-size: 12px; color: #64748b; margin-bottom: 8px;">단위: 억 원 (현재 적용 조건 강조)</p>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>EV/ARR 배수 \\ Forward ARR</th>
                                ${d.arrRange.map(a => `<th>${a}억</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${d.sensitivityMatrix.map(row => `
                                <tr>
                                    <td><strong>${row.multiple.toFixed(1)}배</strong></td>
                                    ${row.values.map(v => `
                                        <td style="${v.isActive ? 'background: #dbeafe; font-weight: bold; color: #1e40af; border: 2px solid #3b82f6;' : ''}">
                                            ${ValuationEngine.formatCurrency(v.equityValue, '', 0)}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            opinionHtml = `
                고성장 B2B SaaS 기업으로서 Rule of 40 점수 ${(d.r40Score * 100).toFixed(1)}%와 NRR ${(d.nrr * 100).toFixed(0)}%의 우수한 고객 리텐션을 입증함.
                글로벌 Peer 평균 대비 Rule of 40 및 NRR 프리미엄 배수가 가산된 <strong>${d.finalMultiple.toFixed(2)}배</strong>의 멀티플을 적용하여 도출된 지분가치 <strong>${ValuationEngine.formatCurrency(d.equityValue)}</strong>은 합리적인 협상 기준점으로 평가됨.
            `;
        } else if (currentTab === 'm4') {
            const d = ValuationEngine.calculateM4();
            modelTitle = 'M4. First Chicago Method (3대 시나리오 확률가중 DCF)';
            targetRound = 'Series B ~ C (AI 로보틱스 / 물류 플랫폼)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">Best 성공 시나리오 (20%)</span>
                        <span class="stat-val" style="color: #059669;">${ValuationEngine.formatCurrency(d.best.npv)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Base 기본 시나리오 (55%)</span>
                        <span class="stat-val" style="color: #2563eb;">${ValuationEngine.formatCurrency(d.base.npv)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Failure 실패 시나리오 (25%)</span>
                        <span class="stat-val" style="color: #dc2626;">${ValuationEngine.formatCurrency(d.failure.npv)}</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #7c3aed; background: #faf5ff;">
                        <span class="stat-label">확률가중 기업가치 (Weighted EV)</span>
                        <span class="stat-val" style="color: #7c3aed;">${ValuationEngine.formatCurrency(d.firstChicagoEV)}</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 시나리오별 파라미터 및 현금흐름 DCF 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>시나리오</th>
                                <th>발생 확률</th>
                                <th>5년차 FCF</th>
                                <th>할인율(WACC)</th>
                                <th>영구성장률(g)</th>
                                <th>잔여가치(TV)</th>
                                <th>시나리오 NPV</th>
                                <th>가중 기여액</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong style="color: #059669;">Best (고성장 성공)</strong></td>
                                <td>${(d.best.prob * 100).toFixed(0)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.best.fcf5)}</td>
                                <td>${(d.best.wacc * 100).toFixed(0)}%</td>
                                <td>${(d.best.g * 100).toFixed(0)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.best.tv)}</td>
                                <td>${ValuationEngine.formatCurrency(d.best.npv)}</td>
                                <td style="font-weight: bold; color: #059669;">${ValuationEngine.formatCurrency(d.weightedBest)}</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #2563eb;">Base (현실적 기본)</strong></td>
                                <td>${(d.base.prob * 100).toFixed(0)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.base.fcf5)}</td>
                                <td>${(d.base.wacc * 100).toFixed(0)}%</td>
                                <td>${(d.base.g * 100).toFixed(0)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.base.tv)}</td>
                                <td>${ValuationEngine.formatCurrency(d.base.npv)}</td>
                                <td style="font-weight: bold; color: #2563eb;">${ValuationEngine.formatCurrency(d.weightedBase)}</td>
                            </tr>
                            <tr>
                                <td><strong style="color: #dc2626;">Failure (하방 위험)</strong></td>
                                <td>${(d.failure.prob * 100).toFixed(0)}%</td>
                                <td>${ValuationEngine.formatCurrency(d.failure.fcf5)}</td>
                                <td>${(d.failure.wacc * 100).toFixed(0)}%</td>
                                <td>0%</td>
                                <td>${ValuationEngine.formatCurrency(d.failure.tv)}</td>
                                <td>${ValuationEngine.formatCurrency(d.failure.npv)}</td>
                                <td style="font-weight: bold; color: #dc2626;">${ValuationEngine.formatCurrency(d.weightedFailure)}</td>
                            </tr>
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="7">확률가중 합산 최종 기업가치 (Weighted Expected Enterprise Value)</td>
                                <td style="font-size: 1.1em; color: #7c3aed;">${ValuationEngine.formatCurrency(d.firstChicagoEV)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;

            opinionHtml = `
                전통적 단일 DCF의 추정 편향을 제거하기 위해 3대 시나리오를 종합 모델링함.
                사업 피벗 및 실패에 따른 25%의 하방 리스크를 전면 반영하면서도, 시장 장악 성공 시의 업사이드(20%)를 함께 가중하여 산출한 <strong>${ValuationEngine.formatCurrency(d.firstChicagoEV)}</strong>은 균형 잡힌 가치평가 결과임.
            `;
        } else if (currentTab === 'm5') {
            const d = ValuationEngine.calculateM5();
            modelTitle = 'M5. BioTech rNPV 타임라인 모델 (위험조정 순현재가치)';
            targetRound = '임상 1상 ~ 2상 (표적항암 신약 파이프라인)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">적용 할인율 (WACC)</span>
                        <span class="stat-val">${(d.wacc * 100).toFixed(0)}%</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">신약 파이프라인 rNPV</span>
                        <span class="stat-val" style="color: #ec4899;">${ValuationEngine.formatCurrency(d.totalPipelineRNPV)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">플랫폼 가치 & 순현금</span>
                        <span class="stat-val">${ValuationEngine.formatCurrency(d.bridgePlatform + d.bridgeCash + d.bridgeDebt)}</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #db2777; background: #fdf2f8;">
                        <span class="stat-label">최종 지분가치 (Equity Value)</span>
                        <span class="stat-val" style="color: #be185d;">${ValuationEngine.formatCurrency(d.finalEquityValue)}</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 임상 단계별 성공 확률(POS) 및 위험조정 현금흐름 타임라인</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>연차</th>
                                <th>임상 마일스톤 이벤트</th>
                                <th>명목 현금흐름</th>
                                <th>누적 성공확률(POS)</th>
                                <th>위험조정 현금흐름</th>
                                <th>할인 rNPV</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.timeline.map(r => `
                                <tr>
                                    <td>${r.year}년차</td>
                                    <td><strong>${r.event}</strong></td>
                                    <td>${ValuationEngine.formatCurrency(r.nominalCF)}</td>
                                    <td>${(r.pos * 100).toFixed(1)}%</td>
                                    <td>${ValuationEngine.formatCurrency(r.riskAdjCF)}</td>
                                    <td style="font-weight: bold; color: ${r.discountedRNPV >= 0 ? '#059669' : '#dc2626'};">${ValuationEngine.formatCurrency(r.discountedRNPV)}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="2">합계</td>
                                <td>${ValuationEngine.formatCurrency(d.totalNominalCF)}</td>
                                <td>-</td>
                                <td>${ValuationEngine.formatCurrency(d.totalRiskAdjCF)}</td>
                                <td style="color: #be185d; font-size: 1.1em;">${ValuationEngine.formatCurrency(d.totalPipelineRNPV)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;

            opinionHtml = `
                글로벌 제약·바이오 표준 평가 기법인 rNPV를 적용하여 각 임상 단계별 역사적 승인 확률(POS)을 현금흐름에 엄격히 할인 적용함.
                파이프라인 rNPV(${ValuationEngine.formatCurrency(d.totalPipelineRNPV)})에 플랫폼 기술가치와 보유 순현금을 합산한 최종 지분가치 <strong>${ValuationEngine.formatCurrency(d.finalEquityValue)}</strong>을 투자 심의 권고 가치로 도출함.
            `;
        } else if (currentTab === 'm6') {
            const d = ValuationEngine.calculateM6();
            modelTitle = 'M6. 유니콘 SOTP(부문별 합산) & 청산우선권(Waterfall) 시뮬레이션';
            targetRound = 'Pre-IPO ~ Late-Stage 유니콘 (복합 비즈니스)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">SOTP 합산 기업가치</span>
                        <span class="stat-val" style="color: #0284c7;">${ValuationEngine.formatCurrency(d.totalSOTPValue)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">가정 Exit 매각가</span>
                        <span class="stat-val">${ValuationEngine.formatCurrency(d.exitValuation)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">Series C 전환 여부</span>
                        <span class="stat-val" style="color: ${d.seriesCConverts ? '#059669' : '#d97706'};">${d.seriesCConverts ? '보통주 전환 행사' : '우선권 행사'}</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #0284c7; background: #f0f9ff;">
                        <span class="stat-label">우선주 총 분배액</span>
                        <span class="stat-val" style="color: #0369a1;">${ValuationEngine.formatCurrency(d.totalPayoutSum)}</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 사업 부문별 가치 합산(SOTP) 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>사업 부문</th>
                                <th>핵심 평가 지표</th>
                                <th>지표 실적</th>
                                <th>적용 멀티플</th>
                                <th>부문별 산정 EV</th>
                                <th>Peer 기준</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.sotpRows.map(r => `
                                <tr>
                                    <td><strong>${r.name}</strong></td>
                                    <td>${r.metricName}</td>
                                    <td>${ValuationEngine.formatCurrency(r.value)}</td>
                                    <td>${r.multiple}배 (${r.base})</td>
                                    <td style="font-weight: bold; color: #0284c7;">${ValuationEngine.formatCurrency(r.ev)}</td>
                                    <td>${r.peer}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr class="total-row">
                                <td colspan="4">총 SOTP 기업가치 (Total Enterprise Value)</td>
                                <td colspan="2" style="font-size: 1.1em; color: #0369a1;">${ValuationEngine.formatCurrency(d.totalSOTPValue)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div class="val-report-section">
                    <h3 class="val-report-section-title">2. 우선주 청산우선권(Liquidation Preference Waterfall) 분배 시뮬레이션</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>주주 등급</th>
                                <th>투자 원금</th>
                                <th>1단계 우선권</th>
                                <th>지분율</th>
                                <th>2단계 잔여배분</th>
                                <th>최종 총 회수액</th>
                                <th>투자 배수 (MOIC)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${d.waterfallRows.map(r => `
                                <tr>
                                    <td><strong>${r.name}</strong></td>
                                    <td>${ValuationEngine.formatCurrency(r.investment)}</td>
                                    <td>${ValuationEngine.formatCurrency(r.step1Pref)}</td>
                                    <td>${(r.ownership * 100).toFixed(1)}%</td>
                                    <td>${ValuationEngine.formatCurrency(r.step2Dist)}</td>
                                    <td style="font-weight: bold; color: #059669;">${ValuationEngine.formatCurrency(r.totalPayout)}</td>
                                    <td style="font-weight: bold; color: #7c3aed;">${r.moic.toFixed(2)}배</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            opinionHtml = `
                SW 플랫폼, 온디바이스 HW, IT 서비스 부문의 사업 특성에 맞춰 각기 다른 피어 멀티플을 적용한 SOTP 가치평가(${ValuationEngine.formatCurrency(d.totalSOTPValue)})를 도출함.
                출구 전략(Exit) 시나리오에 따른 우선주 청산우선권 워터폴 시뮬레이션을 통해 라운드별 실제 회수 수익률(MOIC)과 보통주 주주가치를 사전에 완벽히 검증함.
            `;
        } else {
            // Default: M2 (VC Method)
            const d = ValuationEngine.calculateM2();
            modelTitle = 'M2. VC Method (목표 IRR 기반 시리즈 A 역산 할인 모델)';
            targetRound = 'Series A ~ B (AI 팹리스 / 딥테크 하드웨어)';

            execSummaryHtml = `
                <div class="val-report-summary-box">
                    <div class="val-report-stat-card">
                        <span class="stat-label">금번 라운드 투자금</span>
                        <span class="stat-val">${ValuationEngine.formatCurrency(d.investment)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">적정 Post-money 가치</span>
                        <span class="stat-val" style="color: #059669;">${ValuationEngine.formatCurrency(d.postMoney)}</span>
                    </div>
                    <div class="val-report-stat-card" style="border: 2px solid #2563eb; background: #eff6ff;">
                        <span class="stat-label">금번 라운드 Pre-money</span>
                        <span class="stat-val" style="color: #1e40af;">${ValuationEngine.formatCurrency(d.preMoney)}</span>
                    </div>
                    <div class="val-report-stat-card">
                        <span class="stat-label">목표 회수 배수 (IRR ${(d.targetIRR * 100).toFixed(0)}%)</span>
                        <span class="stat-val" style="color: #d97706;">${d.targetMultiple.toFixed(2)}배</span>
                    </div>
                </div>
            `;

            detailSectionsHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">1. 투자 조건 및 단계별 밸류에이션 역산 내역</h3>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>단계</th>
                                <th>평가 항목</th>
                                <th>계산 공식</th>
                                <th>적용 수치 및 결과</th>
                                <th>비고</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Step 1</td>
                                <td><strong>5년 후 예상 기업가치 (Terminal Value)</strong></td>
                                <td>5년차 순이익 × 목표 PER 배수</td>
                                <td style="font-weight: bold;">${ValuationEngine.formatCurrency(d.exitNetIncome)} × ${d.targetPER}배 = ${ValuationEngine.formatCurrency(d.terminalValue)}</td>
                                <td>코스닥 상장사 피어 평균 PER 25배 적용</td>
                            </tr>
                            <tr>
                                <td>Step 2</td>
                                <td><strong>후속 라운드 희석 감안 TV</strong></td>
                                <td>Terminal Value × (1 - 누적희석률 ${(d.dilution * 100).toFixed(0)}%)</td>
                                <td>${ValuationEngine.formatCurrency(d.dilutedTV)}</td>
                                <td>Series B, C 추가 유치 희석 반영</td>
                            </tr>
                            <tr>
                                <td>Step 3</td>
                                <td><strong>목표 회수 배수 (Target Multiple)</strong></td>
                                <td>(1 + 목표 IRR ${(d.targetIRR * 100).toFixed(0)}%) ^ ${d.holdingYears}년</td>
                                <td style="font-weight: bold; color: #d97706;">${d.targetMultiple.toFixed(2)}배</td>
                                <td>VC 펀드 기준 수익률 충족</td>
                            </tr>
                            <tr style="background: #f0fdf4;">
                                <td>Step 4</td>
                                <td><strong>적정 Post-money 기업가치</strong></td>
                                <td>희석 감안 TV ÷ 목표 회수 배수</td>
                                <td style="font-weight: bold; color: #059669;">${ValuationEngine.formatCurrency(d.postMoney)}</td>
                                <td>투자 직후 적정 기업가치</td>
                            </tr>
                            <tr class="total-row">
                                <td>Step 5</td>
                                <td><strong>금번 제안 Pre-money 기업가치</strong></td>
                                <td>Post-money - 투자금(${ValuationEngine.formatCurrency(d.investment)})</td>
                                <td style="font-size: 1.1em; color: #1e3a8a;"><strong>${ValuationEngine.formatCurrency(d.preMoney)}</strong></td>
                                <td><strong>텀시트(Term Sheet) 제안 밸류</strong></td>
                            </tr>
                            <tr>
                                <td>Step 6</td>
                                <td><strong>금번 라운드 목표 지분율</strong></td>
                                <td>투자금 ÷ Post-money</td>
                                <td>${(d.acquiredShare * 100).toFixed(1)}%</td>
                                <td>투자 집행 직후 확보 지분</td>
                            </tr>
                            <tr>
                                <td>Step 7</td>
                                <td><strong>Exit 시점 예상 잔여 지분율</strong></td>
                                <td>확보 지분율 × (1 - 희석률)</td>
                                <td>${(d.exitShare * 100).toFixed(1)}%</td>
                                <td>5년차 최종 잔여 지분율</td>
                            </tr>
                            <tr>
                                <td>Step 8</td>
                                <td><strong>예상 Exit 회수금액</strong></td>
                                <td>Terminal Value × 잔여 지분율</td>
                                <td style="font-weight: bold; color: #7c3aed;">${ValuationEngine.formatCurrency(d.exitCashFlow)}</td>
                                <td>투자 원금 대비 정확히 ${d.targetMultiple.toFixed(2)}배 달성</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;

            sensitivityHtml = `
                <div class="val-report-section">
                    <h3 class="val-report-section-title">2. 2차원 민감도 분석 매트릭스 (후속 희석률 vs 목표 IRR)</h3>
                    <p style="font-size: 12px; color: #64748b; margin-bottom: 8px;">단위: 억 원 (적정 Pre-money 가치 밴드 / 현재 적용 조건 강조)</p>
                    <table class="val-report-table">
                        <thead>
                            <tr>
                                <th>후속 희석률 \\ 목표 IRR</th>
                                ${d.irrRange.map(irr => `<th>${(irr * 100).toFixed(0)}%</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${d.sensitivityMatrix.map(row => `
                                <tr>
                                    <td><strong>${(row.dilution * 100).toFixed(0)}%</strong></td>
                                    ${row.values.map(v => `
                                        <td style="${v.isActive ? 'background: #dbeafe; font-weight: bold; color: #1e40af; border: 2px solid #3b82f6;' : ''}">
                                            ${ValuationEngine.formatCurrency(v.preMoney, '', 1)}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            opinionHtml = `
                5년 후 상장(IPO) 시점의 예상 순이익 150억 원과 AI 반도체 동종 피어 PER 25배를 적용하여 3,750억 원의 Exit Terminal Value를 도출함.
                시리즈 B, C 추가 유치에 따른 40%의 지분 희석과 당사 목표 IRR 30%를 충족하기 위한 <strong>적정 Pre-money 밸류에이션은 ${ValuationEngine.formatCurrency(d.preMoney)}</strong>으로 산정됨.
                창업자의 요구 밸류가 ${ValuationEngine.formatCurrency(d.preMoney)}를 초과할 경우, 민감도 분석표에 기반하여 후속 희석 방어 조항(Anti-dilution) 및 마일스톤 연동 단가 조정 조건을 계약서에 명시할 것을 제언함.
            `;
        }

        return `
            <div class="val-report-paper">
                <!-- Header -->
                <div class="val-report-header">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: #2563eb; text-transform: uppercase; letter-spacing: 1px;">VC Deal Assessment Memo</span>
                            <h1 class="val-report-title">스타트업 투자 밸류에이션 심사 보고서</h1>
                            <p style="margin: 0; font-size: 13px; color: #64748b;">Startup Valuation & Investment Committee Assessment Memo</p>
                        </div>
                        <div style="text-align: right; font-size: 12px; color: #64748b;">
                            <div>문서번호: VC-VAL-${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}-${Math.floor(1000 + Math.random() * 9000)}</div>
                            <div>발행일자: <strong>${dateStr}</strong></div>
                        </div>
                    </div>
                </div>

                <!-- Meta Table -->
                <table class="val-report-meta-table">
                    <tr>
                        <td class="meta-label">평가 대상</td>
                        <td><strong>(주)혁신 테크놀로지 (Deal Sourcing Target)</strong></td>
                        <td class="meta-label">대상 라운드</td>
                        <td>${targetRound}</td>
                    </tr>
                    <tr>
                        <td class="meta-label">적용 밸류에이션 기법</td>
                        <td><strong>${modelTitle}</strong></td>
                        <td class="meta-label">주관 부서</td>
                        <td>VC 투자심사본부 / AI Deal Analytics Engine</td>
                    </tr>
                    <tr>
                        <td class="meta-label">심사 상태</td>
                        <td colspan="3"><span style="color: #16a34a; font-weight: bold;">● 투자심의위원회(IC) 권고 밸류 산정 완료 (Approved for Term Sheet)</span></td>
                    </tr>
                </table>

                <!-- Executive Summary -->
                <div class="val-report-section">
                    <h3 class="val-report-section-title">📌 Executive Summary (투자 검토 및 적정 가치 요약)</h3>
                    ${execSummaryHtml}
                </div>

                <!-- Detailed Calculations -->
                ${detailSectionsHtml}

                <!-- Sensitivity Analysis -->
                ${sensitivityHtml}

                <!-- Investment Opinion -->
                <div class="val-report-section">
                    <h3 class="val-report-section-title">⚖️ VC 투자심사역 종합 의견 및 텀시트(Term Sheet) 제언</h3>
                    <div class="val-report-opinion-box">
                        ${opinionHtml}
                    </div>
                </div>

                <!-- Signature Footer -->
                <div style="margin-top: 35px; padding-top: 15px; border-top: 1px dashed #cbd5e1; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #64748b;">
                    <div>* 본 보고서는 Deal Sourcing Agent 스타트업 밸류에이션 엔진에 의해 실시간 파라미터 기반으로 산출되었습니다.</div>
                    <div style="text-align: right; font-weight: 600; color: #334155;">VC 투자심의위원회 대표 심사역 (인)</div>
                </div>
            </div>
        `;
    };

    const exportValuationToPDF = () => {
        const reportHtml = generateValuationReportHTML();
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert('팝업 차단이 설정되어 있습니다. 팝업을 허용해주세요.');
            return;
        }

        printWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>스타트업 밸류에이션 투자심사 보고서</title>
                <style>
                    @page {
                        size: A4 portrait;
                        margin: 15mm;
                    }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', 'Malgun Gothic', sans-serif;
                        background: #ffffff;
                        color: #1e293b;
                        padding: 0;
                        margin: 0;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }
                    .val-report-paper {
                        max-width: 100%;
                        background: #ffffff;
                        line-height: 1.6;
                        font-size: 12.5px;
                    }
                    .val-report-header {
                        border-bottom: 2px solid #2563eb;
                        padding-bottom: 12px;
                        margin-bottom: 18px;
                    }
                    .val-report-title {
                        font-size: 22px;
                        font-weight: 800;
                        color: #1e3a8a;
                        margin: 0 0 6px 0;
                    }
                    .val-report-meta-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 18px;
                        background: #f8fafc;
                    }
                    .val-report-meta-table td {
                        padding: 6px 10px;
                        border: 1px solid #cbd5e1;
                        font-size: 11.5px;
                    }
                    .val-report-meta-table .meta-label {
                        background: #f1f5f9;
                        font-weight: 600;
                        color: #475569;
                        width: 18%;
                    }
                    .val-report-section {
                        margin-bottom: 20px;
                    }
                    .val-report-section-title {
                        font-size: 14.5px;
                        font-weight: 700;
                        color: #0f172a;
                        border-left: 4px solid #2563eb;
                        padding-left: 8px;
                        margin: 0 0 10px 0;
                    }
                    .val-report-summary-box {
                        display: grid;
                        grid-template-columns: repeat(4, 1fr);
                        gap: 10px;
                        margin-bottom: 15px;
                    }
                    .val-report-stat-card {
                        background: #f8fafc;
                        border: 1px solid #cbd5e1;
                        border-radius: 6px;
                        padding: 10px;
                        text-align: center;
                    }
                    .val-report-stat-card .stat-label {
                        font-size: 10.5px;
                        color: #64748b;
                        margin-bottom: 4px;
                        display: block;
                    }
                    .val-report-stat-card .stat-val {
                        font-size: 17px;
                        font-weight: 800;
                        color: #1e40af;
                        display: block;
                    }
                    .val-report-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 8px 0 15px 0;
                        font-size: 11.5px;
                    }
                    .val-report-table th {
                        background: #f1f5f9 !important;
                        color: #1e293b;
                        font-weight: 600;
                        border: 1px solid #cbd5e1;
                        padding: 6px 8px;
                        text-align: left;
                    }
                    .val-report-table td {
                        border: 1px solid #e2e8f0;
                        padding: 6px 8px;
                    }
                    .val-report-table tr.total-row {
                        background: #eff6ff !important;
                        font-weight: 700;
                    }
                    .val-report-opinion-box {
                        background: #f0fdf4 !important;
                        border: 1px solid #bbf7d0;
                        border-radius: 6px;
                        padding: 12px 15px;
                        color: #166534;
                        font-size: 12px;
                        line-height: 1.6;
                    }
                </style>
            </head>
            <body>
                ${reportHtml}
                <script>
                    window.onload = function() {
                        setTimeout(function() {
                            window.print();
                        }, 250);
                    };
                </script>
            </body>
            </html>
        `);
        printWindow.document.close();
    };

    const exportValuationToWord = () => {
        const reportHtml = generateValuationReportHTML();
        const today = new Date();
        const dateStr = `${today.getFullYear()}${String(today.getMonth() + 1).padStart(2, '0')}${String(today.getDate()).padStart(2, '0')}`;
        
        const fullWordDoc = `
            <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
            <head>
                <meta charset='utf-8'>
                <title>스타트업 밸류에이션 투자심사 보고서</title>
                <!--[if gte mso 9]>
                <xml>
                <w:WordDocument>
                <w:View>Print</w:View>
                <w:Zoom>100</w:Zoom>
                <w:DoNotOptimizeForBrowser/>
                </w:WordDocument>
                </xml>
                <![endif]-->
                <style>
                    body {
                        font-family: 'Malgun Gothic', '맑은 고딕', 'Arial', sans-serif;
                        font-size: 11pt;
                        line-height: 1.6;
                        color: #1e293b;
                    }
                    h1 { font-size: 20pt; color: #1e3a8a; border-bottom: 2pt solid #2563eb; padding-bottom: 6pt; margin-bottom: 12pt; }
                    h2 { font-size: 14pt; color: #1e40af; margin-top: 15pt; }
                    h3 { font-size: 12pt; color: #0f172a; border-left: 4pt solid #2563eb; padding-left: 6pt; margin: 15pt 0 8pt 0; }
                    table { border-collapse: collapse; width: 100%; margin: 10pt 0; }
                    th, td { border: 1pt solid #cbd5e1; padding: 6pt 8pt; font-size: 10pt; }
                    th { background-color: #f1f5f9; font-weight: bold; color: #334155; }
                    .meta-label { background-color: #f8fafc; font-weight: bold; width: 20%; }
                    .total-row { background-color: #eff6ff; font-weight: bold; color: #1e40af; }
                    .val-report-opinion-box { background-color: #f0fdf4; border: 1pt solid #bbf7d0; padding: 10pt 12pt; color: #166534; margin-top: 8pt; }
                    .val-report-summary-box { margin-bottom: 15pt; }
                    .val-report-stat-card { border: 1pt solid #cbd5e1; background-color: #f8fafc; padding: 8pt; text-align: center; }
                </style>
            </head>
            <body>
                ${reportHtml}
            </body>
            </html>
        `;

        const blob = new Blob(['\ufeff' + fullWordDoc], {
            type: 'application/msword;charset=utf-8'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `스타트업_밸류에이션_투자심사보고서_${dateStr}.doc`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return {
        init,
        renderActiveTab,
        openReportModal,
        exportValuationToPDF,
        exportValuationToWord
    };
})();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ValuationUI.init();
});
