let map;
let currentMarker;
let currentCircle;
let currentData = {};
let seoulGeoJSON = null;

function initMap() {
    map = L.map("map").setView([37.5665, 126.9780], 13);
    L.tileLayer("https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png", {
        attribution: "© Stadia Maps © OpenStreetMap"
    }).addTo(map);
    map.on("click", onMapClick);

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tab = btn.dataset.tab;
            document.getElementById('tab-location').classList.toggle('hidden', tab !== 'location');
            document.getElementById('tab-investment').classList.toggle('hidden', tab !== 'investment');
        });
    });

    const sidebar = document.getElementById('sidebar');
    const mapToggle = document.getElementById('map-toggle');

    document.getElementById('sidebar-toggle').onclick = () => {
        sidebar.classList.remove('open');
        mapToggle.classList.add('visible');
    };
    mapToggle.onclick = () => {
        sidebar.classList.add('open');
        mapToggle.classList.remove('visible');
    };

    document.getElementById('score-breakdown-toggle').onclick = () => {
        const el = document.getElementById('score-breakdown');
        const btn = document.getElementById('score-breakdown-toggle');
        const isHidden = el.classList.contains('hidden');
        el.classList.toggle('hidden');
        btn.textContent = isHidden ? '▲ 점수 산정 근거 닫기' : '▼ 점수 산정 근거 보기';
    };

    // 서울 구 경계 + 라벨 + 외부 어둠 오버레이
    fetch('/static/data/seoul_gu.geojson')
        .then(r => r.json())
        .then(data => {
            seoulGeoJSON = data;

            // 서울 외부 어둡게 (마스크)
            const seoulPolygons = data.features.map(f => f.geometry.coordinates);
            const maskGeoJSON = {
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [
                        [[-180,-90],[180,-90],[180,90],[-180,90],[-180,-90]],
                        ...seoulPolygons.flat(1)
                    ]
                }
            };
            L.geoJSON(maskGeoJSON, {
                style: {
                    color: 'none',
                    fillColor: '#000',
                    fillOpacity: 0.55,
                    stroke: false
                }
            }).addTo(map);

            // 구 경계선만
            L.geoJSON(data, {
                style: {
                    color: '#00BCD4',
                    weight: 2,
                    fillOpacity: 0,
                    opacity: 0.8
                }
            }).addTo(map);

            // 구 이름 라벨
            data.features.forEach(feature => {
                const layer = L.geoJSON(feature);
                const center = layer.getBounds().getCenter();
                const name = feature.properties.name || feature.properties.SIG_KOR_NM || '';
                if (name) {
                    L.marker(center, {
                        icon: L.divIcon({
                            className: 'gu-label',
                            html: name,
                            iconSize: null
                        }),
                        interactive: false
                    }).addTo(map);
                }
            });
        });
}

// 사이드바 열기/닫기
function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('map-toggle').classList.remove('visible');
}
function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('map-toggle').classList.add('visible');
}

// 점수 계산
function calcScore(infraData, landpriceData) {
    // 교통 (25점)
    const nearest = infraData.subway.nearest[0];
    const nearestDist = nearest?.distance ?? 9999;
    const nearestName = nearest?.name ?? '없음';
    const transit = nearestDist <= 200 ? 25
        : nearestDist <= 500 ? 20
        : nearestDist <= 1000 ? 13
        : nearestDist <= 2000 ? 5 : 0;

    // 교육 (20점) - 500m 고정 반경 기준
    const sc = infraData.schools.count_500m ?? 0;
    const edu = sc === 0 ? 0 : sc === 1 ? 10 : sc === 2 ? 16 : 20;

    // 의료 (20점) - 수량(10) + 다양성(10)
    const hc = infraData.hospitals.count_500m ?? 0;
    const lifeQty = hc === 0 ? 0 : hc <= 2 ? 4 : hc <= 5 ? 7 : 10;
    const tb = infraData.hospitals.type_breakdown ?? {};
    const hasMajor = (tb.major?.length ?? 0) > 0;
    const hasGeneral = (tb.general?.length ?? 0) >= 2;
    const hasSpecial = (tb.special?.length ?? 0) > 0;
    const lifeDiversity = (hasMajor ? 5 : 0) + (hasGeneral ? 3 : 0) + (hasSpecial ? 2 : 0);
    const life = lifeQty + lifeDiversity;

    // 자연 (15점) - 500m 고정 반경 기준
    const pc = infraData.parks.count_500m ?? 0;
    const nature = pc === 0 ? 0 : pc === 1 ? 7 : pc === 2 ? 12 : 15;

    // 토지 (20점) - 역방향
    const price = landpriceData.land_price ?? 0;
    const land = price <= 2000000 ? 20
        : price <= 4000000 ? 15
        : price <= 7000000 ? 10
        : price <= 10000000 ? 5 : 2;

    return {
        transit, edu, life, nature, land,
        total: transit + edu + life + nature + land,
        meta: {
            nearestDist, nearestName,
            schoolCount: sc,
            hospitalCount: hc, hasMajor, hasGeneral, hasSpecial,
            parkCount: pc,
            landPrice: price
        }
    };
}

// 근거 텍스트 생성
function buildBreakdown(scores) {
    const m = scores.meta;

    function badge(score, max) {
        const ratio = score / max;
        if (ratio >= 0.8) return 'breakdown-score-green';
        if (ratio >= 0.5) return 'breakdown-score-yellow';
        return 'breakdown-score-red';
    }

    return [
        {
            label: '교통 접근성',
            score: scores.transit,
            max: 25,
            color: badge(scores.transit, 25),
            lines: [
                `최근접 지하철: ${m.nearestName} (${m.nearestDist}m)`,
                m.nearestDist <= 200 ? '도보 3분 이내 → 만점' :
                m.nearestDist <= 500 ? '도보 7분 이내 → 우수' :
                m.nearestDist <= 1000 ? '도보 15분 이내 → 보통' :
                m.nearestDist <= 2000 ? '도보 25분 이내 → 미흡' : '2km 초과 → 불량'
            ]
        },
        {
            label: '교육 환경',
            score: scores.edu,
            max: 20,
            color: badge(scores.edu, 20),
            lines: [
                `반경 500m 내 학교 ${m.schoolCount}개`,
                m.schoolCount === 0 ? '학교 없음 → 0점' :
                m.schoolCount === 1 ? '학교 1개 → 기본' :
                m.schoolCount === 2 ? '학교 2개 → 양호' : '학교 3개+ → 우수'
            ]
        },
        {
            label: '의료 접근성',
            score: scores.life,
            max: 20,
            color: badge(scores.life, 20),
            lines: [
                `반경 500m 내 병원 ${m.hospitalCount}개`,
                `종합병원/상급종합: ${m.hasMajor ? '있음 +5' : '없음 (0점)'}`,
                `의원·치과·한의원 2종+: ${m.hasGeneral ? '충족 +3' : '미충족'}`,
                `요양·보건소 등: ${m.hasSpecial ? '있음 +2' : '없음'}`
            ]
        },
        {
            label: '자연 환경',
            score: scores.nature,
            max: 15,
            color: badge(scores.nature, 15),
            lines: [
                `반경 500m 내 공원 ${m.parkCount}개`,
                m.parkCount === 0 ? '공원 없음 → 0점' :
                m.parkCount === 1 ? '공원 1개 → 기본' :
                m.parkCount === 2 ? '공원 2개 → 양호' : '공원 3개+ → 우수'
            ]
        },
        {
            label: '토지 개발가치',
            score: scores.land,
            max: 20,
            color: badge(scores.land, 20),
            lines: [
                `공시지가 ${m.landPrice.toLocaleString()}원/㎡`,
                m.landPrice <= 2000000 ? '저가 → 개발 여지 매우 높음' :
                m.landPrice <= 4000000 ? '중저가 → 개발 여지 높음' :
                m.landPrice <= 7000000 ? '중가 → 개발 여지 보통' :
                m.landPrice <= 10000000 ? '고가 → 개발 비용 부담' : '초고가 → 개발 비용 매우 높음'
            ]
        }
    ];
}

// 토글 HTML 동적 생성
function renderBreakdown(scores) {
    const items = buildBreakdown(scores);

    const html = items.map(item => `
        <div class="breakdown-item">
            <div class="breakdown-header">
                <span class="breakdown-label">${item.label}</span>
                <span class="breakdown-score score-${item.color}">
                    ${item.score}/${item.max}
                </span>
            </div>
            <div class="breakdown-lines">
                ${item.lines.map(l => `<div class="breakdown-line">└ ${l}</div>`).join('')}
            </div>
        </div>
    `).join('');

    document.getElementById('breakdown-content').innerHTML = html;
}

// 레이더 차트 렌더링
let scoreChart = null;
function renderScoreChart(scores) {
    document.getElementById('score-section').classList.remove('hidden');
    document.getElementById('score-total-badge').textContent
        = `${scores.total} / 100`;

    const ctx = document.getElementById('score-chart').getContext('2d');
    if (scoreChart) scoreChart.destroy();

    scoreChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['교통(25)', '교육(20)', '생활(20)', '자연(15)', '토지(20)'],
            datasets: [{
                label: '부지 점수',
                data: [
                    scores.transit / 25 * 100,
                    scores.edu / 20 * 100,
                    scores.life / 20 * 100,
                    scores.nature / 15 * 100,
                    scores.land / 20 * 100
                ],
                backgroundColor: 'rgba(0, 188, 212, 0.15)',
                borderColor: 'rgba(0, 188, 212, 1)',
                pointBackgroundColor: 'rgba(0, 188, 212, 1)'
            }]
        },
        options: {
            scales: {
                r: {
                    min: 0, max: 100,
                    backgroundColor: 'rgba(0, 188, 212, 0.05)',
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#ccc', font: { size: 11 } },
                    ticks: { display: false }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

async function onMapClick(e) {
    const { lat, lng } = e.latlng;

    // 서울 외부 클릭 차단
    if (seoulGeoJSON) {
        const point = turf.point([lng, lat]);
        const inSeoul = seoulGeoJSON.features.some(f =>
            turf.booleanPointInPolygon(point, f)
        );
        if (!inSeoul) {
            alert("현재 서울 지역만 분석이 가능합니다.\n서울 내 부지를 클릭해주세요.");
            return;
        }
    }

    if (currentMarker) map.removeLayer(currentMarker);
    currentMarker = L.marker([lat, lng]).addTo(map);

    if (currentCircle) map.removeLayer(currentCircle);
    currentCircle = L.circle([lat, lng], {
        radius: 500,
        color: '#00BCD4',
        fillColor: '#00BCD4',
        fillOpacity: 0.05,
        weight: 1.5,
        dashArray: '6, 4'
    }).addTo(map);

    map.flyTo(
        map.unproject(
            map.project([lat, lng], 16).add([210, 0]),
            16
        ),
        16,
        { duration: 0.8 }
    );

    document.getElementById("info-panel").classList.remove("hidden");
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.tab-btn[data-tab="location"]').classList.add('active');
    document.getElementById('tab-location').classList.remove('hidden');
    document.getElementById('tab-investment').classList.add('hidden');
    document.getElementById("address").innerHTML = '<span class="spinner"></span>로딩 중...';
    document.getElementById("zone").textContent = "용도지역: 로딩 중...";
    document.getElementById("landprice").textContent = "공시지가: 로딩 중...";

    try {
        const [geocode, infra, land, landuse, invest] = await Promise.all([
            fetch(`/api/geocode?lat=${lat}&lng=${lng}`).then(r => r.json()),
            fetch(`/api/infrastructure?lat=${lat}&lng=${lng}`).then(r => r.json()),
            fetch(`/api/landprice?lat=${lat}&lng=${lng}`).then(r => r.json()),
            fetch(`/api/landuse?lat=${lat}&lng=${lng}`).then(r => r.json()),
            fetch(`/api/investment?lat=${lat}&lng=${lng}`).then(r => r.json()).catch(() => ({ error: 'fetch_failed' }))
        ]);

        currentData = { infrastructure: infra, landprice: land, landuse: landuse, address: geocode.address || "" };

        document.getElementById("address").textContent = geocode.address || "주소 없음";
        window.currentAddress = geocode.address || "";
        document.getElementById("zone").textContent = `용도지역: ${landuse.zone_name || "정보 없음"}`;
        document.getElementById("landprice").textContent = `공시지가: ${land.land_price ? land.land_price.toLocaleString() + "원/㎡" : "정보 없음"}`;

        const scores = calcScore(infra, land);
        renderScoreChart(scores);
        renderBreakdown(scores);
        renderInvestment(invest);
        openSidebar();

        window.currentScores = scores;

    } catch (err) {
        console.error("데이터 로딩 실패:", err);
        document.getElementById("address").textContent = "데이터 로딩 실패";
    }
}

function renderInvestment(data) {
    if (!data || data.error) {
        document.getElementById('invest-dong').textContent = '데이터 없음';
        ['invest-rent', 'invest-noi', 'invest-caprate', 'invest-confidence'].forEach(id => {
            document.getElementById(id).textContent = '-';
            document.getElementById(id).className = 'invest-value';
        });
        return;
    }

    document.getElementById('invest-dong').textContent =
        `${data.dong} 기준 실거래 데이터 (${data.sample_count}건)`;
    document.getElementById('invest-rent').textContent =
        `${data.avg_monthly_rent.toFixed(1)}만원/월 (전용 ${data.avg_area.toFixed(0)}㎡ 기준)`;
    document.getElementById('invest-noi').textContent =
        data.noi_per_m2 != null ? `㎡당 ${data.noi_per_m2.toFixed(1)}만원/년` : '-';

    const capEl = document.getElementById('invest-caprate');
    if (data.cap_rate != null) {
        capEl.textContent = `${data.cap_rate.toFixed(2)}%`;
        capEl.className = 'invest-value ' + (data.cap_rate >= 4 ? 'high' : data.cap_rate >= 2.5 ? 'medium' : 'low');
    } else {
        capEl.textContent = '-';
        capEl.className = 'invest-value';
    }

    const confEl = document.getElementById('invest-confidence');
    const confMap = { high: '높음 ✓', medium: '보통', low: '낮음 (표본 부족)' };
    confEl.textContent = confMap[data.confidence] || '-';
    confEl.className = 'invest-value ' + (data.confidence || '');
}

async function getRecommendation() {
    const select = document.getElementById("goal-select").value;
    const custom = document.getElementById("goal-custom").value;
    const goal = custom || select;

    if (!goal) {
        alert("개발 목표를 선택하거나 입력해주세요.");
        return;
    }

    if (!currentData.infrastructure) {
        alert("먼저 지도에서 부지를 클릭해주세요.");
        return;
    }

    document.getElementById("result-section").classList.remove("hidden");
    document.getElementById("recommendation-result").textContent = "Gemini 분석 중...";

    try {
        const response = await fetch("/api/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                goal: goal,
                data: currentData,
                scores: window.currentScores,
                address: window.currentAddress || ""
            })
        });

        if (!response.ok) {
            const status = response.status;
            let msg = "추천 실패. 다시 시도해주세요.";
            if (status === 503) msg = "AI 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요.";
            else if (status === 429) msg = "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.";
            document.getElementById("recommendation-result").innerHTML = msg;
            return;
        }

        const result = await response.json();
        document.getElementById("recommendation-result").innerHTML = marked.parse(result.recommendation);
    } catch (err) {
        document.getElementById("recommendation-result").innerHTML =
            "네트워크 오류가 발생했습니다. 인터넷 연결을 확인해주세요.";
    }
}

function downloadPDF() {
    const recommendation = document.getElementById('recommendation-result').innerHTML;
    if (!recommendation || recommendation === 'Gemini 분석 중...') {
        alert('먼저 AI 추천을 받아주세요.');
        return;
    }

    const address = window.currentAddress || '부지';
    const scores = window.currentScores || {};

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Gen-City 분석 보고서</title>
<style>
    body { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; padding: 40px; color: #222; max-width: 800px; margin: 0 auto; }
    h1 { color: #00838f; font-size: 20px; margin-bottom: 4px; }
    .subtitle { color: #888; font-size: 12px; margin-bottom: 24px; }
    .score-box { background: #f5f5f5; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
    .score-total { font-size: 24px; font-weight: bold; color: #00838f; }
    .score-detail { font-size: 12px; color: #555; margin-top: 8px; line-height: 2; }
    .result { font-size: 13px; line-height: 1.9; color: #333; }
    .result h1, .result h2, .result h3 { color: #00838f; font-size: 15px; font-weight: bold; margin: 20px 0 8px; }
    .footer { margin-top: 40px; font-size: 10px; color: #aaa; border-top: 1px solid #eee; padding-top: 12px; }
</style>
</head>
<body>
    <h1>Gen-City | 토지이용계획 분석 보고서</h1>
    <p class="subtitle">부지 주소: ${address}</p>
    <div class="score-box">
        <div class="score-total">종합 점수: ${scores.total ?? '-'} / 100</div>
        <div class="score-detail">
            교통 ${scores.transit ?? '-'}/25 &nbsp;|&nbsp;
            교육 ${scores.edu ?? '-'}/20 &nbsp;|&nbsp;
            생활 ${scores.life ?? '-'}/20 &nbsp;|&nbsp;
            자연 ${scores.nature ?? '-'}/15 &nbsp;|&nbsp;
            토지 ${scores.land ?? '-'}/20
        </div>
    </div>
    <div class="result">${recommendation}</div>
    <div class="footer">본 보고서는 Gen-City AI 분석 결과이며, 실제 개발 계획 수립 시 전문가 검토가 필요합니다.</div>
</body>
</html>
    `);
    printWindow.document.close();
    printWindow.onload = () => {
        printWindow.print();
    };
}

document.addEventListener("DOMContentLoaded", initMap);

function openLimitModal() {
    document.getElementById('limit-modal').classList.remove('hidden');
}
function closeLimitModal() {
    document.getElementById('limit-modal').classList.add('hidden');
}
// 오버레이 클릭 시 닫기
document.getElementById('limit-modal').addEventListener('click', function(e) {
    if (e.target === this) closeLimitModal();
});
