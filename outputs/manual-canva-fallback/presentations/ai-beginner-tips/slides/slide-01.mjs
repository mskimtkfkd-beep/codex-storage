export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: "#EAF8F2" });
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/card-01.png`,
    x: 280,
    y: 0,
    width: 720,
    height: 720,
    fit: "contain",
    alt: "복사 붙여넣기로 시작하세요 카드뉴스",
  });
  return slide;
}
