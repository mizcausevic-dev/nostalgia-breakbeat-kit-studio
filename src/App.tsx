import { Brief, Compare, Drop, Harmony, Hero, KitMap, LongRead, Marquee, Mindmap, Origin, Pipeline, Sound, Validation } from "@/components/Sections";
import { KitLab } from "@/components/KitLab";
import { SiteFooter, SiteHeader } from "@/components/Chrome";
import { LabProvider } from "@/lab";

export default function App() {
  return (
    <LabProvider>
      <SiteHeader />
      <main id="main">
        <Hero />
        <Marquee />
        <KitLab />
        <Compare />
        <KitMap />
        <Mindmap />
        <Harmony />
        <Sound />
        <Pipeline />
        <Validation />
        <Origin />
        <Drop />
        <Brief />
        <LongRead />
      </main>
      <SiteFooter />
    </LabProvider>
  );
}
