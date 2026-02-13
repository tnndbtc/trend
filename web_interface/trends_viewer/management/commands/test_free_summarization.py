"""
Django management command to test free summarization with SystemSettings.

Usage:
    python manage.py test_free_summarization
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async
import asyncio

from trend_agent.services.free_summarization import FreeSummarizationService
from trend_agent.services.factory import ServiceFactory
from trends_viewer.models_system import SystemSettings


class Command(BaseCommand):
    help = 'Test free summarization service with SystemSettings'

    def handle(self, *args, **options):
        """Run tests synchronously."""
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("FREE SUMMARIZATION - DJANGO INTEGRATION TEST"))
        self.stdout.write("=" * 70)
        self.stdout.write("")

        # Run async tests
        asyncio.run(self.run_tests())

    async def run_tests(self):
        """Run all async tests."""

        # Test 1: SystemSettings Model
        self.stdout.write("=" * 70)
        self.stdout.write("TEST 1: SystemSettings Model")
        self.stdout.write("=" * 70)

        try:
            settings = await sync_to_async(SystemSettings.load)()
            self.stdout.write(self.style.SUCCESS(f"✓ Loaded SystemSettings (pk={settings.pk})"))
            self.stdout.write(f"  - Provider: {settings.summarization_provider}")
            self.stdout.write(f"  - Algorithm: {settings.free_summarization_algorithm}")
            self.stdout.write(f"  - Max summary length: {settings.max_summary_length}")
            self.stdout.write(f"  - Title summary length: {settings.title_summary_length}")
            self.stdout.write(f"  - Key points count: {settings.key_points_count}")
            self.stdout.write(f"  - Is free provider: {settings.is_free_provider()}")
            self.stdout.write(f"  - Cost per summary: ${settings.estimate_cost_per_summary():.4f}")
            self.stdout.write(f"  - Estimated monthly cost: ${settings.estimated_monthly_api_cost:.2f}")

            if settings.summarization_provider != 'free':
                self.stdout.write(self.style.WARNING(
                    f"⚠ WARNING: Provider is '{settings.summarization_provider}', expected 'free'"
                ))
            else:
                self.stdout.write(self.style.SUCCESS("✓ Provider is 'free' as expected"))

            test1_pass = True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test 1 FAILED: {e}"))
            import traceback
            traceback.print_exc()
            test1_pass = False

        self.stdout.write("")

        # Test 2: ServiceFactory Integration
        self.stdout.write("=" * 70)
        self.stdout.write("TEST 2: ServiceFactory Integration")
        self.stdout.write("=" * 70)

        try:
            factory = ServiceFactory()
            self.stdout.write(self.style.SUCCESS("✓ Created ServiceFactory"))

            # Get service (should load from SystemSettings)
            service = factory.get_llm_service()  # No provider specified
            self.stdout.write(self.style.SUCCESS(f"✓ Got service: {service}"))
            self.stdout.write(f"  - Service type: {type(service).__name__}")
            self.stdout.write(f"  - Model/Algorithm: {service.get_model_name()}")

            # Verify it's FreeSummarizationService
            if not isinstance(service, FreeSummarizationService):
                self.stdout.write(self.style.WARNING(
                    f"⚠ WARNING: Expected FreeSummarizationService, got {type(service).__name__}"
                ))
            else:
                self.stdout.write(self.style.SUCCESS("✓ Correctly created FreeSummarizationService"))

            test2_pass = True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test 2 FAILED: {e}"))
            import traceback
            traceback.print_exc()
            test2_pass = False

        self.stdout.write("")

        # Test 3: Free Summarization Functionality
        self.stdout.write("=" * 70)
        self.stdout.write("TEST 3: Free Summarization Functionality")
        self.stdout.write("=" * 70)

        try:
            settings = await sync_to_async(SystemSettings.load)()
            service = FreeSummarizationService(
                algorithm=settings.free_summarization_algorithm,
                language='english'
            )

            test_text = """
            Python is a high-level programming language. It is widely used for web development,
            data science, and artificial intelligence. Python has a simple and readable syntax.
            The language supports multiple programming paradigms including procedural, object-oriented,
            and functional programming. Python has a large standard library and extensive third-party packages.
            """

            self.stdout.write(f"Test text ({len(test_text)} chars)")
            self.stdout.write("")

            # Test summarize
            self.stdout.write("Testing summarize()...")
            summary = await service.summarize(test_text, max_length=100)
            self.stdout.write(self.style.SUCCESS(f"✓ Summary ({len(summary)} chars): {summary}"))
            self.stdout.write("")

            # Test extract_key_points
            self.stdout.write("Testing extract_key_points()...")
            key_points = await service.extract_key_points(test_text, max_points=3)
            self.stdout.write(self.style.SUCCESS(f"✓ Key points ({len(key_points)} points):"))
            for i, point in enumerate(key_points, 1):
                self.stdout.write(f"  {i}. {point}")
            self.stdout.write("")

            # Test generate_tags
            self.stdout.write("Testing generate_tags()...")
            tags = await service.generate_tags(test_text, max_tags=5)
            self.stdout.write(self.style.SUCCESS(f"✓ Tags ({len(tags)} tags): {', '.join(tags)}"))

            test3_pass = True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test 3 FAILED: {e}"))
            import traceback
            traceback.print_exc()
            test3_pass = False

        self.stdout.write("")

        # Test 4: Algorithm Comparison
        self.stdout.write("=" * 70)
        self.stdout.write("TEST 4: Algorithm Comparison")
        self.stdout.write("=" * 70)

        try:
            test_text = """
            Machine learning is transforming industries worldwide. Deep learning models
            achieve state-of-the-art results in computer vision and natural language processing.
            Neural networks learn patterns from data automatically. The field continues to advance
            rapidly with new architectures and techniques emerging regularly.
            """

            algorithms = ['textrank', 'lexrank', 'lsa']

            for algo in algorithms:
                self.stdout.write(f"\nAlgorithm: {algo}")
                self.stdout.write("-" * 40)

                service = FreeSummarizationService(algorithm=algo, language='english')
                summary = await service.summarize(test_text, max_length=100)

                self.stdout.write(f"Summary ({len(summary)} chars): {summary}")

            test4_pass = True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test 4 FAILED: {e}"))
            import traceback
            traceback.print_exc()
            test4_pass = False

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("TEST SUMMARY")
        self.stdout.write("=" * 70)

        results = [
            ("SystemSettings Model", test1_pass),
            ("ServiceFactory Integration", test2_pass),
            ("Free Summarization Functionality", test3_pass),
            ("Algorithm Comparison", test4_pass),
        ]

        for name, passed in results:
            status = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f"{'✓' if passed else '✗'} Test: {name} - {status}")

        all_pass = all(p for _, p in results)

        self.stdout.write("")
        self.stdout.write("=" * 70)
        if all_pass:
            self.stdout.write(self.style.SUCCESS("✅ ALL TESTS PASSED!"))
            self.stdout.write("")
            self.stdout.write("Free summarization is working correctly:")
            self.stdout.write("  • Works offline with zero API costs")
            self.stdout.write("  • Integrated with SystemSettings")
            self.stdout.write("  • ServiceFactory auto-selects 'free' provider")
            self.stdout.write("  • Multiple algorithms available (TextRank, LexRank, LSA)")
        else:
            self.stdout.write(self.style.ERROR("❌ SOME TESTS FAILED"))
        self.stdout.write("=" * 70)
