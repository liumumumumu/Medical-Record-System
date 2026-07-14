package com.medicalrecord.backend;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = {
		"app.demo-user.enabled=false",
		"app.jwt.secret=context-test-secret-that-is-long-enough-for-hs256-signing",
		"app.ai.mode=mock",
		"spring.data.mongodb.auto-index-creation=false",
		"spring.data.mongodb.uri=mongodb://127.0.0.1:27019/medical_records_context_test?serverSelectionTimeoutMS=50",
		"logging.level.org.mongodb.driver=OFF"
})
class MedicalRecordBackendApplicationTests {

	@Test
	void contextLoads() {
	}

}
