// avatar.js
import * as THREE from "https://cdn.skypack.dev/three@0.160";
import { AvatarLoader, VisemePlayer } from "https://cdn.jsdelivr.net/npm/@readyplayerme/viseme@2.2/dist/viseme.esm.js";
import { FaceModel } from "https://cdn.jsdelivr.net/npm/kalidokit@1.1.2/dist/kalidokit.esm.js";

/**
 * Initialise scene & avatar, return a callback that drives viseme weights.
 * @param {HTMLCanvasElement} canvas
 * @returns {(weights: Record<string, number>) => void}
 */
export async function createAvatar(canvas) {
  // --- scene ----------------------------------------------------------
  const scene    = new THREE.Scene();
  const camera   = new THREE.PerspectiveCamera(25, 1, 0.1, 1000);
  camera.position.set(0, 1.5, 2.4);

  const renderer = new THREE.WebGLRenderer({ canvas, alpha:true, antialias:true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(canvas.clientWidth, canvas.clientHeight);

  // lighting
  scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.2));

  // --- avatar ---------------------------------------------------------
  // 👉  Replace this URL with YOUR Ready Player Me glb link
  const avatarUrl = "https://models.readyplayer.me/64abc1234567890abcdef.glb";
  const avatar = await new AvatarLoader().load(avatarUrl);
  scene.add(avatar);

  // viseme player maps ARKit blend‑shape weights onto the mesh
  const visemePlayer = new VisemePlayer(avatar);

  // --- render loop ----------------------------------------------------
  function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }
  animate();

  // expose a driver fn
  return (weights) => visemePlayer.play(weights);
}

/**
 * Convert audio analyser data to ARKit viseme weights using Kalidokit.
 * @param {Uint8Array} freqData
 * @returns {Record<string, number>}
 */
export function analyserToViseme(freqData) {
  return FaceModel.animate(freqData);
}
