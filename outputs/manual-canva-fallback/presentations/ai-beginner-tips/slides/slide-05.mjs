export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: "#FFF8D8" });
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/card-05.png`,
    x: 280,
    y: 0,
    width: 720,
    height: 720,
    fit: "contain",
    alt: "매일 5분이라도 써보세요 카드뉴스",
  });
  return slide;
}
