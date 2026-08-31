const length = document.getElementById("length");
const height = document.getElementById("height");
const gates = document.getElementById("gates");
const terrain = document.getElementById("terrain");

const lengthValue = document.getElementById("lengthValue");
const heightValue = document.getElementById("heightValue");
const gatesValue = document.getElementById("gatesValue");
const postsValue = document.getElementById("postsValue");
const railsValue = document.getElementById("railsValue");
const moodValue = document.getElementById("moodValue");
const quip = document.getElementById("quip");

const quips = {
  flat: "Flat terrain: smooth install, smooth operator, smooth little grin.",
  sloped: "Sloped terrain: still classy, just with more contour and more dramatic music.",
  rocky: "Rocky terrain: for when the ground fights back but the estimate stays composed.",
  mixed: "Mixed terrain: a little chaos, a lot of confidence, zero borrowed ideas."
};

function update() {
  const lengthFt = Number(length.value);
  const heightFt = Number(height.value);
  const gateCount = Number(gates.value);
  const estimatedPosts = Math.ceil(lengthFt / 8) + 1 + gateCount;
  const estimatedRails = Math.ceil(lengthFt / 8) * (heightFt >= 6 ? 3 : 2);

  lengthValue.textContent = `${lengthFt} ft`;
  heightValue.textContent = `${heightFt} ft`;
  gatesValue.textContent = String(gateCount);
  postsValue.textContent = String(estimatedPosts);
  railsValue.textContent = String(estimatedRails);

  const moodScore = estimatedPosts + estimatedRails + gateCount * 4;
  moodValue.textContent = moodScore > 80 ? "Intense" : moodScore > 55 ? "Spicy" : "Mild";
  quip.textContent = quips[terrain.value];
}

[length, height, gates].forEach((element) => {
  element.addEventListener("input", update);
});
terrain.addEventListener("change", update);

update();
