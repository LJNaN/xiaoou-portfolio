const { BASE } = require('../../config/index');
const api = require('../../utils/api');

const FALLBACK_BOX = 422; // 拿不到原图宽高时的兜底高度（rpx），按 16:9 算
const SOLID_AT = 8; // 滚过这么多 px 就让导航栏变实
const TOP_AT = 1200; // 滚过这么多 px 才显示「回到顶部」

// 图片满宽 = 750rpx，按原图比例把高度先算出来占住位置，
// 这样图片加载完不会有布局回弹 —— 长流滚动「不抖」就靠这个。
function boxHeight(image) {
  if (!image || !image.w || !image.h) return FALLBACK_BOX;
  return Math.round((750 * image.h) / image.w);
}

// 章节色块上的字用黑还是白，按亮度自动挑：目录页那四个底色深浅差很多
function textOn(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? '#111111' : '#FFFFFF';
}

Page({
  data: {
    ready: false,
    error: false,
    statusBarHeight: 20,
    navHeight: 44,
    navTotal: 64,
    navSolid: false,
    progress: 0,
    showTop: false,
    profile: {},
    cover: null,
    resume: null,
    blocks: [],
    previewUrls: [],
  },

  onLoad() {
    this.setupNav();
    this.loadContent();
  },

  loadContent() {
    api
      .load((content) => this.apply(content))
      .catch(() => {
        // 有缓存的话页面已经渲染出来了，这里只处理「连缓存都没有」的情况
        if (!this.data.ready) this.setData({ error: true });
      });
  },

  setupNav() {
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const statusBarHeight = win.statusBarHeight || 20;
    this.windowHeight = win.windowHeight;

    // 导航栏高度跟右上角胶囊对齐，否则不同机型上标题位置会跳
    let navHeight = 44;
    try {
      const capsule = wx.getMenuButtonBoundingClientRect();
      if (capsule && capsule.height && capsule.top > statusBarHeight) {
        navHeight = (capsule.top - statusBarHeight) * 2 + capsule.height;
      }
    } catch (e) {
      // 开发者工具偶尔量不到胶囊位置，用 44 兜底
    }

    this.setData({ statusBarHeight, navHeight, navTotal: statusBarHeight + navHeight });
  },

  apply(content) {
    const url = (path) => (path ? BASE + path : '');
    const profile = content.profile || {};
    const pages = (content.pages || []).filter((page) => !page.missing);

    const categories = {};
    (content.categories || []).forEach((cat) => {
      categories[cat.id] = cat;
    });

    // 把「章节条」和「作品页」压成一维数组，页面里只用一个 wx:for 顺序渲染
    const blocks = [];
    const opened = {};
    pages.forEach((page) => {
      if (page.role === 'cover') return; // 封面单独做首屏

      if (page.category && !opened[page.category]) {
        const cat = categories[page.category];
        if (cat) {
          blocks.push({
            type: 'chapter',
            key: `chapter-${cat.id}`,
            index: cat.index,
            name: cat.name,
            en: cat.en,
            color: cat.color,
            textColor: textOn(cat.color),
          });
        }
        opened[page.category] = true;
      }

      blocks.push({
        type: 'page',
        key: `page-${page.id}`,
        id: page.id,
        title: page.title,
        note: page.note,
        thumb: url(page.thumb),
        full: url(page.full),
        boxH: boxHeight(page),
      });
    });

    const coverPage = pages.find((page) => page.role === 'cover');
    const cover = coverPage
      ? { thumb: url(coverPage.thumb), full: url(coverPage.full), boxH: boxHeight(coverPage) }
      : null;

    const resumeRaw = content.resume && !content.resume.missing ? content.resume : null;
    const resume = resumeRaw
      ? { thumb: url(resumeRaw.thumb), full: url(resumeRaw.full), boxH: boxHeight(resumeRaw) }
      : null;

    // 放大预览的顺序跟页面里看到的一致：封面 → 简历 → 画册 02…18，
    // 传全了就能左右滑连续看完整本
    const previewUrls = [];
    if (cover) previewUrls.push(cover.full);
    if (resume) previewUrls.push(resume.full);
    pages.forEach((page) => {
      if (page.role !== 'cover') previewUrls.push(url(page.full));
    });

    this.setData({ ready: true, error: false, profile, cover, resume, blocks, previewUrls });
    wx.nextTick(() => this.measure());
  },

  // 量一次内容总高度，滚动进度条要用
  measure() {
    wx.createSelectorQuery()
      .select('.page')
      .boundingClientRect((rect) => {
        if (rect && rect.height) {
          this.maxScroll = Math.max(1, rect.height - this.windowHeight);
        }
      })
      .exec();
  },

  onPageScroll(e) {
    const top = e.scrollTop;

    const solid = top > SOLID_AT;
    if (solid !== this.data.navSolid) this.setData({ navSolid: solid });

    const showTop = top > TOP_AT;
    if (showTop !== this.data.showTop) this.setData({ showTop });

    // 只在整数百分比变化时更新，一次长滑最多一百来次很小的 setData
    const percent = this.maxScroll
      ? Math.min(100, Math.round((top / this.maxScroll) * 100))
      : 0;
    if (percent !== this.data.progress) this.setData({ progress: percent });
  },

  onPreview(e) {
    const current = e.currentTarget.dataset.full;
    if (!current) return;
    wx.previewImage({
      urls: this.data.previewUrls,
      current,
      showmenu: true,
    });
  },

  onCall() {
    const phoneNumber = this.data.profile.phone;
    if (phoneNumber) wx.makePhoneCall({ phoneNumber });
  },

  onCopyEmail() {
    const data = this.data.profile.email;
    if (data) wx.setClipboardData({ data });
  },

  onCopyWechat() {
    const data = this.data.profile.wechat;
    if (data) wx.setClipboardData({ data });
  },

  onBackTop() {
    wx.pageScrollTo({ scrollTop: 0, duration: 300 });
  },

  onRetry() {
    this.setData({ error: false });
    this.loadContent();
  },

  onShareAppMessage() {
    const { profile, cover } = this.data;
    return {
      title: `${profile.name} · ${profile.title}｜作品集`,
      path: '/pages/index/index',
      imageUrl: cover ? cover.thumb : '',
    };
  },

  onShareTimeline() {
    const { profile } = this.data;
    return {
      title: `${profile.name} · ${profile.title}｜平面设计作品集`,
    };
  },
});
