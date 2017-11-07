import java.io.IOException;
import java.io.File;
import java.util.logging.Logger;
import java.util.logging.Handler;
import java.util.logging.Level;
import org.lttng.ust.agent.jul.LttngLogHandler;

public class App
{
    private static final int answer = 42;

    public static void main(String[] argv) throws Exception
    {
	int nrIter = Integer.parseInt(argv[0]);
	String sync_first_tp_hit_path = null;
	String sync_wait_before_last = null;

	if (argv.length > 1) {
		sync_first_tp_hit_path = argv[1];
	}
	if (argv.length > 2) {
		sync_wait_before_last = argv[2];
	}

        // Create a logger
        Logger logger = Logger.getLogger("jello");
	logger.setLevel(Level.INFO);

	Handler lttngHandler = new LttngLogHandler();

	logger.addHandler(lttngHandler);

	for (int i=0; i < 0 || i < nrIter; i++) {
		if ( i >= 0 && i == nrIter -1 && sync_wait_before_last != null) {
			File f = new File(sync_wait_before_last);
			while (!f.exists()) {
				Thread.sleep(1);
			}
		}
		logger.info("logging the world");
		logger.warning("some warning");
		logger.severe("error!");
		if (i == 0 && sync_first_tp_hit_path != null) {
			File f = new File(sync_first_tp_hit_path);
			f.createNewFile();
		}
	}

        // Not mandatory, but cleaner
	logger.removeHandler(lttngHandler);
	lttngHandler.close();
    }
}
