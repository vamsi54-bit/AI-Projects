"use client";

import {
  Bounds,
  Center,
  useAnimations,
  useGLTF,
} from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import Link from "next/link";
import {
  Suspense,
  useEffect,
  useRef,
  useState,
} from "react";
import * as THREE from "three";

const MODEL_PATH = "/models/rose-knight/scene.gltf";

function KnightModel() {
  const group = useRef<THREE.Group>(null!);
  const { scene, animations } = useGLTF(MODEL_PATH);
  const { actions } = useAnimations(animations, group);

  useEffect(() => {
    const action = Object.values(actions).find(Boolean);

    action?.reset().fadeIn(0.5).play();

    return () => {
      action?.fadeOut(0.3);
    };
  }, [actions]);

  useFrame((state, delta) => {
    const { x, y } = state.pointer;
    const time = state.clock.elapsedTime;

    // Strong 90% horizontal mouse response.
    const targetY =
      x * 0.9 + Math.sin(time * 0.35) * 0.08;

    const targetX = y * 0.35;

    group.current.rotation.y = THREE.MathUtils.damp(
      group.current.rotation.y,
      targetY,
      7,
      delta,
    );

    group.current.rotation.x = THREE.MathUtils.damp(
      group.current.rotation.x,
      targetX,
      7,
      delta,
    );

    group.current.position.y =
      Math.sin(time * 0.8) * 0.07;
  });

  return (
    <group ref={group}>
      <Bounds fit clip observe margin={1.25}>
        <Center>
          <primitive object={scene} />
        </Center>
      </Bounds>
    </group>
  );
}

export default function EmotionCore() {
  const [desktop, setDesktop] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 769px)");

    const update = () => setDesktop(media.matches);

    update();
    media.addEventListener("change", update);

    return () => media.removeEventListener("change", update);
  }, []);

  if (!desktop) return null;

  return (
    <div className="knight-experience">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 38 }}
        dpr={[1, 1.5]}
        eventSource={document.documentElement}
        eventPrefix="client"
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
      >
        <ambientLight intensity={2.2} />

        <directionalLight
          position={[4, 6, 5]}
          intensity={4}
          color="#ffffff"
        />

        <pointLight
          position={[-3, 2, 4]}
          intensity={18}
          color="#67e8f9"
        />

        <pointLight
          position={[3, -1, 3]}
          intensity={12}
          color="#ff647c"
        />

        <Suspense fallback={null}>
          <KnightModel />
        </Suspense>
      </Canvas>

      <div className="knight-speech">
        <span className="speech-dot" />

        <strong>
          Curious what your expression reveals?
        </strong>

        <p>
          Let Emora Vision read the moment.
        </p>

        <Link href="/detect">
          Try live detection →
        </Link>
      </div>
    </div>
  );
}

useGLTF.preload(MODEL_PATH);