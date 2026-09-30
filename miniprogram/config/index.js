// 全项目只有这一个地方需要改地址。
//
// dev  ：本地起后端（server/ 目录），开发者工具里要勾「不校验合法域名」
// prod ：网关后面的线上地址。域名已备案、也已加进小程序后台的
//        「request 合法域名」和「downloadFile 合法域名」—— 线上就用它，别改
const ENV = 'prod';

const BASE = {
  dev: 'http://127.0.0.1:5003',
  prod: 'https://www.jnnnn.top',
}[ENV];

module.exports = {
  ENV,
  BASE,
  // 接口路径前缀与 gateway/routes.inc 里配的那两段保持一致
  API: `${BASE}/portfolio-api`,
  IMG: `${BASE}/portfolio-images`,
};
