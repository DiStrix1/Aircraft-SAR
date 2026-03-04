import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import ProblemSection from "@/components/ProblemSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import AccuracySection from "@/components/AccuracySection";
import MissionControl from "@/components/MissionControl";
import FooterSection from "@/components/FooterSection";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <ProblemSection />
      <HowItWorksSection />
      <AccuracySection />
      <MissionControl />
      <FooterSection />
    </div>
  );
};

export default Index;
