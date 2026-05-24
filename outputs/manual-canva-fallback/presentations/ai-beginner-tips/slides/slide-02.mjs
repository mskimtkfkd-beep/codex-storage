export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: "#FFF0E8" });
  await ctx.addImage(slide, {
    path: `${ctx.assetDir}/card-02.png`,
    x: 280,
    y: 0,
    width: 720,
    height: 720,
    fit: "contain",
    alt: "한 번에 다 시키지 마세요 카드뉴스",
  });
  return slide;
}
