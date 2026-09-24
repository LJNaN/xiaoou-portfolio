// 全项目只有这一个地方需要改地址。
//
// dev  ：本地起后端（server/ 目录），开发者工具里要勾「不校验合法域名」
// prod ：网关后面的线上地址，需要在小程序后台把域名加进
//        「request 合法域名」和「downloadFile 合法域名」
// ip   ：**临时**用裸 IP 直连，只给真机调试用。
//        jnnnn.top 备案没下来之前，带域名的请求会被阿里云按 SNI 重置
//        （ERR_CONNECTION_RESET），裸 IP 不带 SNI / Host 是 IP，不受影响。
//        所以在开发者工具或「真机调试」里勾上「不校验合法域名」才能用，
//        正式发布必须切回 prod。备案下来后这个分支就可以删掉。
const ENV = 'ip';

const BASE = {
  dev: 'http://127.0.0.1:5003',
  prod: 'https://www.jnnnn.top',
  ip: 'http://47.109.29.134',
}[ENV];

module.exports = {
  ENV,
  BASE,
  // 接口路径前缀与 gateway/routes.inc 里配的那两段保持一致
  API: `${BASE}/portfolio-api`,
  IMG: `${BASE}/portfolio-images`,
};
