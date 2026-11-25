// 탭 5. 연결 설정 › AI 모델: OpenAI·Claude 카드([이 AI 사용], 모델 고르기, [연결 검사]). 담당: KHS (HS 요청 11/25)
import { ConnectionsView } from "@/components/connections/ConnectionsView";

export default function AiModelPage() {
  return <ConnectionsView part="ai" />;
}
