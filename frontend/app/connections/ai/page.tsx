// 탭 6. 연결 설정 › AI 모델: OpenAI 카드 하나(모델 고르기, [연결 검사]). OpenAI만 사용: HS 결정 11/26. 담당: KHS
import { ConnectionsView } from "@/components/connections/ConnectionsView";

export default function AiModelPage() {
  return <ConnectionsView part="ai" />;
}
