const { API } = require('../config/index');

const CACHE_KEY = 'portfolio_content_v1';

function readCache() {
  try {
    const cached = wx.getStorageSync(CACHE_KEY);
    return cached && cached.pages ? cached : null;
  } catch (e) {
    return null;
  }
}

function writeCache(content) {
  try {
    wx.setStorageSync(CACHE_KEY, content);
  } catch (e) {
    // 存不下就算了，下次照样能从网络拿
  }
}

function fetchContent() {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API}/content`,
      method: 'GET',
      timeout: 10000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.pages) {
          resolve(res.data);
        } else {
          reject(new Error(`HTTP ${res.statusCode}`));
        }
      },
      fail(err) {
        // 排查真机请求失败用：把确切的 errMsg 打出来（真机调试时在 PC 的 console 里看）
        console.error('[portfolio] 请求失败', `${API}/content`, err && err.errMsg, JSON.stringify(err));
        reject(new Error(err.errMsg || '网络异常'));
      },
    });
  });
}

/**
 * 先用本地缓存渲染（二次打开基本秒开），再拉最新的。
 * 内容没变（版本号一致）就不回调第二次，免得白重渲染一遍、图片闪一下。
 *
 * @param {(content: object) => void} onUpdate
 * @returns {Promise<object>} 网络请求的结果
 */
function load(onUpdate) {
  const cached = readCache();
  if (cached) onUpdate(cached);

  return fetchContent().then((fresh) => {
    if (!cached || cached.version !== fresh.version) {
      writeCache(fresh);
      onUpdate(fresh);
    }
    return fresh;
  });
}

module.exports = { load };
