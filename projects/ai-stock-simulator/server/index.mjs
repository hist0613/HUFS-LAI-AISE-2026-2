import { createApp } from "./app.mjs";

const port = Number(process.env.PORT) || 3000;

createApp().listen(port, () => {
  console.log(`AI Stock Simulator 서버 실행 중: http://localhost:${port}`);
});
