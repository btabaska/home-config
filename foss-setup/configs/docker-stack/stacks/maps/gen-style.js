const b = require("@protomaps/basemaps");
const flavor = b.namedFlavor("light");
const style = {
  version: 8,
  glyphs: "https://maps.tabaska.us/fonts/{fontstack}/{range}.pbf",
  sprite: "https://maps.tabaska.us/sprites/light",
  sources: {
    protomaps: {
      type: "vector",
      url: "https://maps.tabaska.us/pmtiles/us.json",
      attribution: "<a href=\"https://protomaps.com\">Protomaps</a> © <a href=\"https://openstreetmap.org/copyright\">OpenStreetMap</a>"
    }
  },
  layers: b.layers("protomaps", flavor, { lang: "en" })
};
process.stdout.write(JSON.stringify(style, null, 1));
