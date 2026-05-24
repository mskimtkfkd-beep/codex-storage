export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: "#EAF5FF" });
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/card-03.png`,
    x: 280,
    y: 0,
    width: 720,
    height: 720,
    fit: "contain",
    alt: "한국어로 말해도 다 알아들어요 카드뉴스",
  });
  return slide;
}
