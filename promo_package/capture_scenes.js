const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const EDGE_PATH = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const HTML_FILE = path.resolve(__dirname, 'Tax_Assistant_Demo_V4_180s.html');
const OUTPUT_DIR = path.resolve(__dirname, 'captured_scenes');
const userDataDir = path.join(__dirname, 'edge_capture_profile');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function getBrowserWsUrl(port) {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      const data = await res.json();
      if (data.webSocketDebuggerUrl) return data.webSocketDebuggerUrl;
    } catch (e) {}
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('Edge CDP 연결 실패');
}

function createCDPSession(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 1;
  const callbacks = new Map();

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && callbacks.has(msg.id)) {
      const { resolve, reject } = callbacks.get(msg.id);
      callbacks.delete(msg.id);
      if (msg.error) reject(msg.error);
      else resolve(msg.result);
    }
  };

  const readyPromise = new Promise((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = (err) => reject(err);
  });

  const send = async (method, params = {}, sessionId = undefined) => {
    await readyPromise;
    return new Promise((resolve, reject) => {
      const msgId = id++;
      callbacks.set(msgId, { resolve, reject });
      const payload = { id: msgId, method, params };
      if (sessionId) payload.sessionId = sessionId;
      ws.send(JSON.stringify(payload));
    });
  };

  return { ws, send };
}

async function run() {
  console.log('1. Edge 브라우저 시작...');
  const edge = spawn(EDGE_PATH, [
    '--headless=new',
    '--remote-debugging-port=9222',
    '--disable-gpu',
    '--hide-scrollbars',
    '--window-size=1920,1080',
    '--force-device-scale-factor=1.5',
    `--user-data-dir=${userDataDir}`,
    'about:blank'
  ]);

  try {
    const browserWsUrl = await getBrowserWsUrl(9222);
    console.log('2. 브라우저 디버거 연결 성공');
    const browserSession = createCDPSession(browserWsUrl);

    // 새 탭 생성 및 연결
    const { targetId } = await browserSession.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await browserSession.send('Target.attachToTarget', { targetId, flatten: true });

    const send = (method, params) => browserSession.send(method, params, sessionId);

    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');

    // 뷰포트 해상도 설정 (고화질 FHD)
    await send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1.5,
      mobile: false
    });

    console.log(`3. HTML 페이지 로딩: ${HTML_FILE}`);
    const fileUrl = 'file:///' + HTML_FILE.replace(/\\/g, '/');
    await send('Page.navigate', { url: fileUrl });

    // 페이지 로드 대기
    await new Promise(r => setTimeout(r, 1200));

    // BGM 음소거 및 애니메이션 안정화 주입
    await send('Runtime.evaluate', {
      expression: `
        if (typeof musicOn !== 'undefined') musicOn = false;
        if (typeof voiceOn !== 'undefined') voiceOn = false;
        if (document.getElementById('bgm')) {
          document.getElementById('bgm').pause();
          document.getElementById('bgm').muted = true;
        }
      `
    });

    // 캡처할 장면 리스트 정의
    const scenesToCapture = [
      {
        id: '01A',
        name: 'Scene_01A_오프닝_세무판단은_검색으로_끝나지_않습니다',
        evalJs: `
          jump(2.2);
          const s1 = $('scene1');
          s1.classList.add('active', 'intro-line');
          s1.classList.remove('intro-reveal');
        `,
        waitMs: 300
      },
      {
        id: '01B',
        name: 'Scene_01B_문제_검토과정은_흩어져_있습니다',
        evalJs: `
          jump(6.0);
          const s1 = $('scene1');
          s1.classList.add('active', 'intro-reveal');
          s1.classList.remove('intro-line');
        `,
        waitMs: 300
      },
      {
        id: '02',
        name: 'Scene_02_해법_한건의_질문을_검증된_조직지식으로',
        evalJs: `jump(16.0);`,
        waitMs: 300
      },
      {
        id: '03',
        name: 'Scene_03_고도화_승인지식이_축적되는_구조',
        evalJs: `jump(27.0);`,
        waitMs: 300
      },
      {
        id: '04',
        name: 'Scene_04_질문_자연어_세무판례_심층분석_입력',
        evalJs: `
          jump(42.0);
          // 질문 문장 전체 채우기
          const q = '거래처 계약 중도해지 위약금은 법인세법상 손금으로 인정될 수 있는가?';
          $('typedQuery').textContent = q;
        `,
        waitMs: 300
      },
      {
        id: '05',
        name: 'Scene_05_내부지식_승인지식_우선검색',
        evalJs: `jump(58.0);`,
        waitMs: 300
      },
      {
        id: '06',
        name: 'Scene_06_공식근거_국가법령_공식DB_탐색',
        evalJs: `jump(78.0);`,
        waitMs: 300
      },
      {
        id: '07',
        name: 'Scene_07_검토안_실무판단을_위한_구조화된_검토안',
        evalJs: `jump(98.0);`,
        waitMs: 300
      },
      {
        id: '08',
        name: 'Scene_08_저장_검토이력_자동저장_승인대기',
        evalJs: `jump(118.0);`,
        waitMs: 300
      },
      {
        id: '09',
        name: 'Scene_09_승인_사람_중심의_지식_승인',
        evalJs: `jump(134.0);`,
        waitMs: 300
      },
      {
        id: '10',
        name: 'Scene_10_재사용_승인된_지식의_재사용',
        evalJs: `jump(156.0);`,
        waitMs: 300
      },
      {
        id: '11',
        name: 'Scene_11_피드백_품질개선과_재검토',
        evalJs: `jump(172.0);`,
        waitMs: 300
      },
      {
        id: '12',
        name: 'Scene_12_신뢰_통제_구조_설계',
        evalJs: `jump(188.0);`,
        waitMs: 300
      },
      {
        id: '13',
        name: 'Scene_13_엔딩_TAX_ASSISTANT_조직의지식',
        evalJs: `
          jump(205.0);
          // 엔딩 요소 즉시 표시 스타일 적용
          const copy = document.querySelector('.finale-copy');
          if (copy) { copy.style.opacity = '1'; copy.style.transform = 'scale(1)'; }
          const beam = document.querySelector('.finale-beam');
          if (beam) { beam.style.height = '52%'; beam.style.opacity = '0.7'; }
          const line = document.querySelector('.finale-line');
          if (line) { line.style.width = '360px'; }
        `,
        waitMs: 400
      }
    ];

    console.log(`4. 총 ${scenesToCapture.length}개 장면 캡처 시작...`);

    for (let i = 0; i < scenesToCapture.length; i++) {
      const scene = scenesToCapture[i];
      console.log(` [${i + 1}/${scenesToCapture.length}] ${scene.name} 캡처 중...`);

      // 장면 활성화 및 설정 실행
      await send('Runtime.evaluate', {
        expression: `
          (function() {
            ${scene.evalJs}
            // transition 일시 제거하여 즉각 선명하게 렌더링
            const style = document.getElementById('_capture_style') || document.createElement('style');
            style.id = '_capture_style';
            style.textContent = '.scene { transition: none !important; }';
            document.head.appendChild(style);
          })()
        `
      });

      await new Promise(r => setTimeout(r, scene.waitMs));

      // 뷰포트(동영상 본체) 위치 구하기
      const rectResult = await send('Runtime.evaluate', {
        expression: `
          (function() {
            const vp = document.getElementById('viewport');
            const r = vp.getBoundingClientRect();
            return { x: r.left, y: r.top, width: r.width, height: r.height };
          })()
        `,
        returnByValue: true
      });

      const rect = rectResult.result.value;

      // 16:9 비디오 뷰포트만 고화질 스크린샷 캡처
      const screenshot = await send('Page.captureScreenshot', {
        format: 'png',
        clip: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          scale: 1.5
        }
      });

      const imgBuffer = Buffer.from(screenshot.data, 'base64');
      const filename = `${scene.name}.png`;
      const filePath = path.join(OUTPUT_DIR, filename);
      fs.writeFileSync(filePath, imgBuffer);
      console.log(`      ✓ 저장 완료: ${filename} (${(imgBuffer.length / 1024).toFixed(1)} KB)`);
    }

    console.log(`\n🎉 모든 장면(${scenesToCapture.length}개) 캡처가 성공적으로 완료되었습니다!`);
    console.log(`저장 위치: ${OUTPUT_DIR}`);

  } finally {
    edge.kill();
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch (e) {}
    try { fs.unlinkSync(path.join(__dirname, 'test_cdp.js')); } catch (e) {}
  }
}

run().catch(err => {
  console.error('실행 중 오류 발생:', err);
  process.exit(1);
});
