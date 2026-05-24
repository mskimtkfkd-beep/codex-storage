export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: "#F1ECFF" });
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/card-04.png`,
    x: 280,
    y: 0,
    width: 720,
    height: 720,
    fit: "contain",
    alt: "결과가 이상하면 다시 물어보세요 카드뉴스",
  });
  return slide;
}
