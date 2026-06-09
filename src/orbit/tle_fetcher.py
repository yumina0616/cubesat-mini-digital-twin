"""
tle_fetcher.py - Celestrak에서 실시간 TLE 데이터를 가져옵니다.

[사용 방법]
    from src.orbit.tle_fetcher import TLEFetcher

    # 위성 이름으로 검색
    tle = TLEFetcher.fetch_by_name("ISS")
    tle = TLEFetcher.fetch_by_norad_id(25544)   # ISS NORAD ID

[데이터 출처]
    Celestrak (https://celestrak.org)
    - 회원가입 없이 무료로 사용 가능
    - NORAD 카탈로그 번호 또는 위성 이름으로 검색 가능

[NORAD ID 찾는 법]
    https://celestrak.org/satcat/search.php 에서 위성 이름으로 검색
    주요 위성 NORAD ID:
        ISS          : 25544
        Hubble (HST) : 20580
        DOVE-1       : 39418
        LEMUR-2-JOEL : 41789
        NOAA-18      : 28654
"""

import requests
from datetime import datetime, timezone

# Celestrak API 엔드포인트
CELESTRAK_BASE = "https://celestrak.org"
CELESTRAK_GP   = f"{CELESTRAK_BASE}/NORAD/elements/gp.php"  # ?CATNR=<ID>&FORMAT=TLE

# 요청 타임아웃 (초)
TIMEOUT = 10


class TLEFetcher:
    """
    Celestrak에서 실시간 TLE를 가져오는 유틸리티 클래스.
    네트워크가 없는 환경에서는 자동으로 오프라인 캐시를 반환합니다.
    """

    # 오프라인 폴백 캐시 (네트워크 없을 때 사용)
    # 최신 TLE로 주기적으로 업데이트 권장
    _OFFLINE_CACHE = {
        25544: {
            "name": "ISS (ZARYA)",
            "line1": "1 25544U 98067A   24365.50000000  .00016717  00000-0  10270-3 0  9993",
            "line2": "2 25544  51.6400 208.9163 0006317  86.9959 273.1588 15.49815849421234",
            "source": "offline_cache",
        },
        39418: {
            "name": "DOVE-1",
            "line1": "1 39418U 13066L   24001.50000000  .00001234  00000-0  12345-3 0  9991",
            "line2": "2 39418  97.4000 100.0000 0010000  90.0000 270.0000 15.19000000123456",
            "source": "offline_cache",
        },
    }

    @staticmethod
    def fetch_by_norad_id(norad_id: int) -> dict:
        """
        NORAD Catalog ID로 최신 TLE를 Celestrak에서 가져옵니다.

        Args:
            norad_id (int): NORAD 카탈로그 번호 (예: 25544 = ISS)

        Returns:
            dict: {
                'name'   : 위성 이름,
                'line1'  : TLE 첫 번째 줄,
                'line2'  : TLE 두 번째 줄,
                'source' : 'celestrak' 또는 'offline_cache',
                'fetched_at': 가져온 시각 (UTC)
            }
        """
        url = f"{CELESTRAK_GP}?CATNR={norad_id}&FORMAT=TLE"

        try:
            print(f"[TLEFetcher] Celestrak에서 NORAD {norad_id} 조회 중...")
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            lines = [l.strip() for l in response.text.strip().split('\n') if l.strip()]

            if len(lines) < 3:
                raise ValueError(f"TLE 형식 오류: {len(lines)}줄 반환됨")

            # TLE 형식 검증
            if not lines[1].startswith('1 ') or not lines[2].startswith('2 '):
                raise ValueError("올바른 TLE 형식이 아닙니다.")

            result = {
                'name'      : lines[0],
                'line1'     : lines[1],
                'line2'     : lines[2],
                'source'    : 'celestrak',
                'fetched_at': datetime.now(timezone.utc).isoformat(),
            }
            print(f"[TLEFetcher] 성공: {result['name']}")
            print(f"  Epoch: {lines[1][18:32].strip()}")
            return result

        except Exception as e:
            print(f"[TLEFetcher] 네트워크 오류: {e}")
            print(f"[TLEFetcher] 오프라인 캐시로 폴백합니다.")
            return TLEFetcher._get_from_cache(norad_id)

    @staticmethod
    def fetch_by_name(name: str) -> dict:
        """
        위성 이름으로 TLE를 검색합니다.
        이름으로 검색이 실패하면 주요 위성 NORAD ID 매핑을 사용합니다.

        Args:
            name (str): 위성 이름 (예: "ISS", "DOVE-1")
        """
        # 이름 → NORAD ID 매핑
        NAME_TO_NORAD = {
            "ISS"      : 25544,
            "ZARYA"    : 25544,
            "HST"      : 20580,
            "HUBBLE"   : 20580,
            "DOVE-1"   : 39418,
            "LEMUR-2"  : 41789,
            "NOAA-18"  : 28654,
        }

        norad_id = NAME_TO_NORAD.get(name.upper().strip())
        if norad_id:
            return TLEFetcher.fetch_by_norad_id(norad_id)

        # NORAD ID 매핑에 없으면 Celestrak 이름 검색
        try:
            url = f"{CELESTRAK_GP}?NAME={requests.utils.quote(name)}&FORMAT=TLE"
            print(f"[TLEFetcher] Celestrak 이름 검색: '{name}'")
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()

            lines = [l.strip() for l in response.text.strip().split('\n') if l.strip()]
            if len(lines) >= 3 and lines[1].startswith('1 '):
                return {
                    'name'      : lines[0],
                    'line1'     : lines[1],
                    'line2'     : lines[2],
                    'source'    : 'celestrak',
                    'fetched_at': datetime.now(timezone.utc).isoformat(),
                }
            raise ValueError("검색 결과 없음")

        except Exception as e:
            print(f"[TLEFetcher] 검색 실패: {e}")
            raise RuntimeError(f"'{name}' TLE를 찾을 수 없습니다. NORAD ID로 직접 검색해보세요.")

    @staticmethod
    def fetch_group(group: str) -> list:
        """
        Celestrak 위성 그룹 전체 TLE를 가져옵니다.

        주요 그룹:
            'stations'  : 우주 정거장 (ISS 등)
            'active'    : 현재 운용 중인 모든 위성
            'cubesat'   : CubeSat 전체
            'planet'    : Planet Labs (Dove 위성들)
            'spire'     : Spire Global (LEMUR 위성들)

        Returns:
            list of dict: TLE 딕셔너리 리스트
        """
        gp_url = f"{CELESTRAK_GP}?GROUP={group}&FORMAT=TLE"

        try:
            print(f"[TLEFetcher] 그룹 '{group}' 조회 중...")
            response = requests.get(gp_url, timeout=TIMEOUT)
            response.raise_for_status()

            lines   = [l.strip() for l in response.text.strip().split('\n') if l.strip()]
            results = []
            for i in range(0, len(lines) - 2, 3):
                if lines[i+1].startswith('1 ') and lines[i+2].startswith('2 '):
                    results.append({
                        'name' : lines[i],
                        'line1': lines[i+1],
                        'line2': lines[i+2],
                        'source': 'celestrak',
                    })

            print(f"[TLEFetcher] {len(results)}개 위성 TLE 수신")
            return results

        except Exception as e:
            print(f"[TLEFetcher] 그룹 조회 실패: {e}")
            return []

    @staticmethod
    def _get_from_cache(norad_id: int) -> dict:
        """오프라인 캐시에서 TLE 반환"""
        if norad_id in TLEFetcher._OFFLINE_CACHE:
            data = TLEFetcher._OFFLINE_CACHE[norad_id].copy()
            data['fetched_at'] = 'offline_cache'
            print(f"[TLEFetcher] 캐시 사용: {data['name']}")
            return data
        raise RuntimeError(
            f"NORAD {norad_id}의 TLE를 캐시에서도 찾을 수 없습니다. "
            f"인터넷 연결을 확인하거나 TLE를 직접 입력해주세요."
        )

    @staticmethod
    def validate_tle(line1: str, line2: str) -> bool:
        """
        TLE 형식 유효성 검사

        Returns:
            bool: 유효하면 True
        """
        try:
            if not (line1.strip().startswith('1 ') and line2.strip().startswith('2 ')):
                return False
            if len(line1.strip()) != 69 or len(line2.strip()) != 69:
                return False
            # 체크섬 검증
            for line in [line1.strip(), line2.strip()]:
                checksum = sum(
                    int(c) if c.isdigit() else (1 if c == '-' else 0)
                    for c in line[:-1]
                ) % 10
                if checksum != int(line[-1]):
                    return False
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

    print("=== TLEFetcher 테스트 ===\n")

    # 1. NORAD ID로 가져오기
    tle = TLEFetcher.fetch_by_norad_id(25544)
    print(f"\n위성명 : {tle['name']}")
    print(f"Line 1 : {tle['line1']}")
    print(f"Line 2 : {tle['line2']}")
    print(f"출처   : {tle['source']}")

    # 2. TLELoader와 연동
    from src.orbit.tle_loader import TLELoader
    from src.orbit.orbit_simulator import OrbitSimulator

    loader = TLELoader.from_string(tle['name'], tle['line1'], tle['line2'])
    ic     = loader.get_initial_conditions()
    sim    = OrbitSimulator(
        altitude=ic['altitude_2d'],
        sim_time=ic['period_min'] * 60,
        method='rk4',
        x0=ic['x0'], y0=ic['y0'],
        vx0=ic['vx0'], vy0=ic['vy0'],
    )
    data = sim.run()
    print(f"\n시뮬 평균 고도: {data['altitude'].mean()/1000:.1f} km")
    print(f"에너지 드리프트: {(data['energy'][-1]-data['energy'][0])/abs(data['energy'][0])*100:.6f}%")